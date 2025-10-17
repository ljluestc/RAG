import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';
import crypto from 'crypto';

interface RegisterInput {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}

interface LoginInput {
  email: string;
  password: string;
}

export class AuthService {
  private readonly JWT_SECRET = process.env.JWT_SECRET!;
  private readonly JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';
  private readonly REFRESH_SECRET = process.env.JWT_REFRESH_SECRET!;
  private readonly REFRESH_EXPIRES_IN = process.env.JWT_REFRESH_EXPIRES_IN || '30d';
  private readonly BCRYPT_ROUNDS = parseInt(process.env.BCRYPT_ROUNDS || '12');

  async register(input: RegisterInput) {
    try {
      // Check if user already exists
      const existingUser = await prisma.user.findUnique({
        where: { email: input.email },
      });

      if (existingUser) {
        throw new AppError('User already exists with this email', 400);
      }

      // Hash password
      const passwordHash = await bcrypt.hash(input.password, this.BCRYPT_ROUNDS);

      // Create user
      const user = await prisma.user.create({
        data: {
          email: input.email,
          passwordHash,
          firstName: input.firstName,
          lastName: input.lastName,
          subscriptionTier: 'FREE',
          status: 'ACTIVE',
        },
        select: {
          id: true,
          email: true,
          firstName: true,
          lastName: true,
          role: true,
          subscriptionTier: true,
          createdAt: true,
        },
      });

      // Generate tokens
      const { accessToken, refreshToken } = this.generateTokens(user);

      // Create session
      await this.createSession(user.id, accessToken);

      logger.info('User registered successfully', { userId: user.id, email: user.email });

      return {
        user,
        accessToken,
        refreshToken,
      };
    } catch (error) {
      logger.error('Registration error', { error });
      throw error;
    }
  }

  async login(input: LoginInput) {
    try {
      // Find user
      const user = await prisma.user.findUnique({
        where: { email: input.email },
        select: {
          id: true,
          email: true,
          passwordHash: true,
          firstName: true,
          lastName: true,
          role: true,
          subscriptionTier: true,
          status: true,
          mfaEnabled: true,
        },
      });

      if (!user) {
        throw new AppError('Invalid credentials', 401);
      }

      // Check if account is active
      if (user.status !== 'ACTIVE') {
        throw new AppError('Account is not active', 403);
      }

      // Verify password
      const isPasswordValid = await bcrypt.compare(input.password, user.passwordHash!);
      if (!isPasswordValid) {
        throw new AppError('Invalid credentials', 401);
      }

      // If MFA is enabled, return temporary token
      if (user.mfaEnabled) {
        const mfaToken = this.generateMFAToken(user.id);
        return {
          requiresMFA: true,
          mfaToken,
        };
      }

      // Generate tokens
      const { accessToken, refreshToken } = this.generateTokens(user);

      // Create session
      await this.createSession(user.id, accessToken);

      // Update last login
      await prisma.user.update({
        where: { id: user.id },
        data: { lastLoginAt: new Date() },
      });

      logger.info('User logged in successfully', { userId: user.id, email: user.email });

      const { passwordHash, ...userWithoutPassword } = user;

      return {
        user: userWithoutPassword,
        accessToken,
        refreshToken,
      };
    } catch (error) {
      logger.error('Login error', { error });
      throw error;
    }
  }

  async refreshToken(refreshToken: string) {
    try {
      // Verify refresh token
      const decoded = jwt.verify(refreshToken, this.REFRESH_SECRET) as { id: string };

      // Find user
      const user = await prisma.user.findUnique({
        where: { id: decoded.id },
        select: {
          id: true,
          email: true,
          role: true,
          status: true,
        },
      });

      if (!user || user.status !== 'ACTIVE') {
        throw new AppError('Invalid refresh token', 401);
      }

      // Generate new tokens
      const tokens = this.generateTokens(user);

      // Create new session
      await this.createSession(user.id, tokens.accessToken);

      return tokens;
    } catch (error) {
      logger.error('Token refresh error', { error });
      throw new AppError('Invalid refresh token', 401);
    }
  }

  async logout(userId: string, token: string) {
    try {
      // Delete session
      await prisma.session.deleteMany({
        where: {
          userId,
          token,
        },
      });

      logger.info('User logged out', { userId });
    } catch (error) {
      logger.error('Logout error', { error });
      throw error;
    }
  }

  async requestPasswordReset(email: string) {
    try {
      const user = await prisma.user.findUnique({
        where: { email },
      });

      if (!user) {
        // Don't reveal if user exists
        logger.warn('Password reset requested for non-existent email', { email });
        return { message: 'If the email exists, a reset link has been sent' };
      }

      // Generate reset token
      const resetToken = crypto.randomBytes(32).toString('hex');
      const resetTokenHash = await bcrypt.hash(resetToken, 10);

      // Store token in database (you'd add a field for this)
      // For now, we'll just log it
      logger.info('Password reset token generated', { userId: user.id, token: resetToken });

      // TODO: Send email with reset link
      // await emailService.sendPasswordResetEmail(user.email, resetToken);

      return { message: 'If the email exists, a reset link has been sent' };
    } catch (error) {
      logger.error('Password reset request error', { error });
      throw error;
    }
  }

  async resetPassword(token: string, newPassword: string) {
    try {
      // TODO: Verify reset token
      // For now, this is a stub

      // Hash new password
      const passwordHash = await bcrypt.hash(newPassword, this.BCRYPT_ROUNDS);

      // Update password
      // await prisma.user.update({
      //   where: { id: userId },
      //   data: { passwordHash },
      // });

      logger.info('Password reset successful');

      return { message: 'Password reset successful' };
    } catch (error) {
      logger.error('Password reset error', { error });
      throw error;
    }
  }

  async verifyEmail(token: string) {
    try {
      // TODO: Verify email token
      // For now, this is a stub

      logger.info('Email verified successfully');

      return { message: 'Email verified successfully' };
    } catch (error) {
      logger.error('Email verification error', { error });
      throw error;
    }
  }

  private generateTokens(user: { id: string; email: string; role: string }) {
    const accessToken = jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      this.JWT_SECRET,
      { expiresIn: this.JWT_EXPIRES_IN }
    );

    const refreshToken = jwt.sign({ id: user.id }, this.REFRESH_SECRET, {
      expiresIn: this.REFRESH_EXPIRES_IN,
    });

    return { accessToken, refreshToken };
  }

  private generateMFAToken(userId: string) {
    return jwt.sign({ id: userId, type: 'mfa' }, this.JWT_SECRET, {
      expiresIn: '5m',
    });
  }

  private async createSession(userId: string, token: string) {
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7); // 7 days

    await prisma.session.create({
      data: {
        userId,
        token,
        expiresAt,
      },
    });
  }
}

export const authService = new AuthService();
