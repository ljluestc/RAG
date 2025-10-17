import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';

export class UserService {
  async getUserById(userId: string) {
    try {
      const user = await prisma.user.findUnique({
        where: { id: userId },
        include: {
          profile: true,
          preferences: true,
          subscription: true,
        },
      });

      if (!user) {
        throw new AppError('User not found', 404);
      }

      const { passwordHash, ...userWithoutPassword } = user;
      return userWithoutPassword;
    } catch (error) {
      logger.error('Get user error', { error, userId });
      throw error;
    }
  }

  async updateUser(userId: string, data: any) {
    try {
      const user = await prisma.user.update({
        where: { id: userId },
        data,
        select: {
          id: true,
          email: true,
          firstName: true,
          lastName: true,
          phoneNumber: true,
          avatar: true,
          role: true,
          subscriptionTier: true,
          updatedAt: true,
        },
      });

      logger.info('User updated', { userId });
      return user;
    } catch (error) {
      logger.error('Update user error', { error, userId });
      throw error;
    }
  }

  async deleteUser(userId: string) {
    try {
      await prisma.user.update({
        where: { id: userId },
        data: { status: 'DELETED' },
      });

      logger.info('User deleted', { userId });
      return { message: 'User deleted successfully' };
    } catch (error) {
      logger.error('Delete user error', { error, userId });
      throw error;
    }
  }

  async getProfile(userId: string) {
    try {
      let profile = await prisma.profile.findUnique({
        where: { userId },
      });

      if (!profile) {
        // Create default profile
        profile = await prisma.profile.create({
          data: { userId },
        });
      }

      return profile;
    } catch (error) {
      logger.error('Get profile error', { error, userId });
      throw error;
    }
  }

  async updateProfile(userId: string, data: any) {
    try {
      const profile = await prisma.profile.upsert({
        where: { userId },
        update: data,
        create: {
          userId,
          ...data,
        },
      });

      logger.info('Profile updated', { userId });
      return profile;
    } catch (error) {
      logger.error('Update profile error', { error, userId });
      throw error;
    }
  }

  async getPreferences(userId: string) {
    try {
      let preferences = await prisma.preferences.findUnique({
        where: { userId },
      });

      if (!preferences) {
        // Create default preferences
        preferences = await prisma.preferences.create({
          data: { userId },
        });
      }

      return preferences;
    } catch (error) {
      logger.error('Get preferences error', { error, userId });
      throw error;
    }
  }

  async updatePreferences(userId: string, data: any) {
    try {
      const preferences = await prisma.preferences.upsert({
        where: { userId },
        update: data,
        create: {
          userId,
          ...data,
        },
      });

      logger.info('Preferences updated', { userId });
      return preferences;
    } catch (error) {
      logger.error('Update preferences error', { error, userId });
      throw error;
    }
  }

  async calculateProfileCompleteness(userId: string) {
    try {
      const profile = await this.getProfile(userId);
      const user = await prisma.user.findUnique({ where: { id: userId } });

      let completeness = 0;
      const fields = [
        user?.firstName,
        user?.lastName,
        user?.phoneNumber,
        profile?.headline,
        profile?.summary,
        profile?.location,
        profile?.currentJobTitle,
        profile?.workExperience && Array.isArray(profile.workExperience) && profile.workExperience.length > 0,
        profile?.education && Array.isArray(profile.education) && profile.education.length > 0,
        profile?.skills && Array.isArray(profile.skills) && profile.skills.length > 0,
      ];

      completeness = (fields.filter(Boolean).length / fields.length) * 100;

      // Update profile completeness
      await prisma.profile.update({
        where: { userId },
        data: { completeness: Math.round(completeness) },
      });

      return Math.round(completeness);
    } catch (error) {
      logger.error('Calculate profile completeness error', { error, userId });
      throw error;
    }
  }
}

export const userService = new UserService();
