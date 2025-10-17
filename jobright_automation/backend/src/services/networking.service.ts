import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { aiService } from './ai.service';

export class NetworkingService {
  async createConnection(
    userId: string,
    data: {
      name: string;
      title?: string;
      company?: string;
      linkedinUrl?: string;
      email?: string;
      phone?: string;
      type: string;
      notes?: string;
    }
  ) {
    try {
      const connection = await prisma.connection.create({
        data: {
          userId,
          ...data,
          status: 'PENDING',
          strength: 0,
        },
      });

      logger.info('Connection created', { userId, connectionId: connection.id });

      return connection;
    } catch (error) {
      logger.error('Create connection error', { error, userId });
      throw error;
    }
  }

  async getUserConnections(userId: string, filters?: { status?: string; type?: string }) {
    try {
      const where: any = { userId };

      if (filters?.status) {
        where.status = filters.status;
      }

      if (filters?.type) {
        where.type = filters.type;
      }

      const connections = await prisma.connection.findMany({
        where,
        orderBy: [{ strength: 'desc' }, { createdAt: 'desc' }],
      });

      return connections;
    } catch (error) {
      logger.error('Get connections error', { error, userId });
      throw error;
    }
  }

  async updateConnectionStatus(connectionId: string, userId: string, status: string) {
    try {
      const connection = await prisma.connection.updateMany({
        where: {
          id: connectionId,
          userId,
        },
        data: { status },
      });

      logger.info('Connection status updated', { connectionId, userId, status });

      return connection;
    } catch (error) {
      logger.error('Update connection status error', { error, connectionId });
      throw error;
    }
  }

  async generateOutreachMessage(connection: any, context?: string): Promise<string> {
    const systemPrompt = `You are a professional networking expert. Generate a personalized LinkedIn connection request message or outreach email that is professional, genuine, and likely to get a response.`;

    const messages = [
      {
        role: 'user' as const,
        content: `Connection: ${JSON.stringify(connection, null, 2)}\nContext: ${context || 'General networking'}\n\nGenerate a professional outreach message (150-300 characters for LinkedIn).`,
      },
    ];

    return await aiService.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.8,
      maxTokens: 500,
    });
  }

  async discoverAlumni(userId: string, targetCompany: string) {
    try {
      const profile = await prisma.profile.findUnique({
        where: { userId },
      });

      // In a real implementation, this would search LinkedIn or other sources
      // for alumni from the user's schools who work at the target company

      logger.info('Alumni discovery initiated', { userId, targetCompany });

      return {
        message: 'Alumni discovery feature - to be integrated with LinkedIn API',
        targetCompany,
        userEducation: profile?.education || [],
      };
    } catch (error) {
      logger.error('Discover alumni error', { error, userId });
      throw error;
    }
  }

  async trackCommunication(connectionId: string, userId: string, communication: any) {
    try {
      const connection = await prisma.connection.findFirst({
        where: {
          id: connectionId,
          userId,
        },
      });

      if (!connection) {
        throw new Error('Connection not found');
      }

      const communications = Array.isArray(connection.communications)
        ? [...connection.communications, communication]
        : [communication];

      await prisma.connection.update({
        where: { id: connectionId },
        data: {
          communications: communications as any,
          lastContactedAt: new Date(),
        },
      });

      logger.info('Communication tracked', { connectionId, userId });

      return communication;
    } catch (error) {
      logger.error('Track communication error', { error, connectionId });
      throw error;
    }
  }
}

export const networkingService = new NetworkingService();
