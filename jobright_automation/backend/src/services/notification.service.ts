import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { notificationQueue } from '../config/queues';

export class NotificationService {
  async createNotification(
    userId: string,
    type: string,
    title: string,
    message: string,
    data?: any,
    channels: string[] = ['IN_APP']
  ) {
    try {
      const notification = await prisma.notification.create({
        data: {
          userId,
          type,
          title,
          message,
          data,
          channels,
        },
      });

      // Queue notification for delivery
      await notificationQueue.add('send-notification', {
        notificationId: notification.id,
        userId,
        channels,
      });

      logger.info('Notification created', { userId, notificationId: notification.id, type });

      return notification;
    } catch (error) {
      logger.error('Create notification error', { error, userId });
      throw error;
    }
  }

  async getUserNotifications(userId: string, unreadOnly: boolean = false) {
    try {
      const where: any = { userId };
      if (unreadOnly) {
        where.read = false;
      }

      const notifications = await prisma.notification.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        take: 50,
      });

      return notifications;
    } catch (error) {
      logger.error('Get notifications error', { error, userId });
      throw error;
    }
  }

  async markAsRead(notificationId: string, userId: string) {
    try {
      await prisma.notification.updateMany({
        where: {
          id: notificationId,
          userId,
        },
        data: {
          read: true,
          readAt: new Date(),
        },
      });

      logger.info('Notification marked as read', { notificationId, userId });
    } catch (error) {
      logger.error('Mark notification read error', { error, notificationId });
      throw error;
    }
  }

  async markAllAsRead(userId: string) {
    try {
      await prisma.notification.updateMany({
        where: {
          userId,
          read: false,
        },
        data: {
          read: true,
          readAt: new Date(),
        },
      });

      logger.info('All notifications marked as read', { userId });
    } catch (error) {
      logger.error('Mark all notifications read error', { error, userId });
      throw error;
    }
  }

  async getUnreadCount(userId: string): Promise<number> {
    try {
      return await prisma.notification.count({
        where: {
          userId,
          read: false,
        },
      });
    } catch (error) {
      logger.error('Get unread count error', { error, userId });
      return 0;
    }
  }
}

export const notificationService = new NotificationService();
