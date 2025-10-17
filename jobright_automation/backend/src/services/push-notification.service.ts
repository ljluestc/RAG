import admin from 'firebase-admin';
import { logger } from '../config/logger';

// Initialize Firebase Admin SDK
const FIREBASE_PROJECT_ID = process.env.FIREBASE_PROJECT_ID || '';
const FIREBASE_PRIVATE_KEY = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n') || '';
const FIREBASE_CLIENT_EMAIL = process.env.FIREBASE_CLIENT_EMAIL || '';

let firebaseApp: admin.app.App | null = null;

if (FIREBASE_PROJECT_ID && FIREBASE_PRIVATE_KEY && FIREBASE_CLIENT_EMAIL) {
  try {
    firebaseApp = admin.initializeApp({
      credential: admin.credential.cert({
        projectId: FIREBASE_PROJECT_ID,
        privateKey: FIREBASE_PRIVATE_KEY,
        clientEmail: FIREBASE_CLIENT_EMAIL,
      }),
    });
  } catch (error: any) {
    logger.error('Failed to initialize Firebase', { error: error.message });
  }
}

export interface PushNotification {
  title: string;
  body: string;
  data?: Record<string, string>;
  imageUrl?: string;
  clickAction?: string;
}

export class PushNotificationService {
  private isConfigured: boolean;

  constructor() {
    this.isConfigured = !!firebaseApp;
    if (!this.isConfigured) {
      logger.warn('Firebase not configured - push notifications disabled');
    }
  }

  // Send push notification to single device
  async sendToDevice(token: string, notification: PushNotification): Promise<boolean> {
    if (!this.isConfigured || !firebaseApp) {
      logger.warn('Cannot send push notification - Firebase not configured');
      return false;
    }

    try {
      const message: admin.messaging.Message = {
        token,
        notification: {
          title: notification.title,
          body: notification.body,
          imageUrl: notification.imageUrl,
        },
        data: notification.data,
        webpush: notification.clickAction
          ? {
              fcmOptions: {
                link: notification.clickAction,
              },
            }
          : undefined,
        android: {
          notification: {
            sound: 'default',
            priority: 'high',
          },
        },
        apns: {
          payload: {
            aps: {
              sound: 'default',
              badge: 1,
            },
          },
        },
      };

      const response = await admin.messaging().send(message);

      logger.info('Push notification sent successfully', {
        messageId: response,
        title: notification.title,
      });

      return true;
    } catch (error: any) {
      logger.error('Failed to send push notification', {
        error: error.message,
        code: error.code,
        title: notification.title,
      });

      // If token is invalid, we should remove it from database
      if (error.code === 'messaging/invalid-registration-token' ||
          error.code === 'messaging/registration-token-not-registered') {
        logger.info('Invalid FCM token detected', { token });
        // In a real implementation, trigger removal from database
      }

      return false;
    }
  }

  // Send push notification to multiple devices
  async sendToMultipleDevices(
    tokens: string[],
    notification: PushNotification
  ): Promise<{ success: number; failure: number }> {
    if (!this.isConfigured || !firebaseApp) {
      logger.warn('Cannot send push notifications - Firebase not configured');
      return { success: 0, failure: tokens.length };
    }

    try {
      const message: admin.messaging.MulticastMessage = {
        tokens,
        notification: {
          title: notification.title,
          body: notification.body,
          imageUrl: notification.imageUrl,
        },
        data: notification.data,
        webpush: notification.clickAction
          ? {
              fcmOptions: {
                link: notification.clickAction,
              },
            }
          : undefined,
      };

      const response = await admin.messaging().sendEachForMulticast(message);

      logger.info('Push notifications sent', {
        success: response.successCount,
        failure: response.failureCount,
        total: tokens.length,
      });

      // Log failed tokens
      if (response.failureCount > 0) {
        response.responses.forEach((resp, idx) => {
          if (!resp.success) {
            logger.warn('Failed to send to token', {
              token: tokens[idx],
              error: resp.error?.message,
            });
          }
        });
      }

      return {
        success: response.successCount,
        failure: response.failureCount,
      };
    } catch (error: any) {
      logger.error('Failed to send push notifications', {
        error: error.message,
        tokenCount: tokens.length,
      });

      return { success: 0, failure: tokens.length };
    }
  }

  // Send push notification to topic
  async sendToTopic(topic: string, notification: PushNotification): Promise<boolean> {
    if (!this.isConfigured || !firebaseApp) {
      logger.warn('Cannot send push notification - Firebase not configured');
      return false;
    }

    try {
      const message: admin.messaging.Message = {
        topic,
        notification: {
          title: notification.title,
          body: notification.body,
          imageUrl: notification.imageUrl,
        },
        data: notification.data,
      };

      const response = await admin.messaging().send(message);

      logger.info('Push notification sent to topic', {
        messageId: response,
        topic,
        title: notification.title,
      });

      return true;
    } catch (error: any) {
      logger.error('Failed to send push notification to topic', {
        error: error.message,
        topic,
      });

      return false;
    }
  }

  // Subscribe token to topic
  async subscribeToTopic(tokens: string[], topic: string): Promise<boolean> {
    if (!this.isConfigured || !firebaseApp) {
      logger.warn('Cannot subscribe to topic - Firebase not configured');
      return false;
    }

    try {
      const response = await admin.messaging().subscribeToTopic(tokens, topic);

      logger.info('Subscribed to topic', {
        topic,
        successCount: response.successCount,
        failureCount: response.failureCount,
      });

      return response.successCount > 0;
    } catch (error: any) {
      logger.error('Failed to subscribe to topic', {
        error: error.message,
        topic,
      });

      return false;
    }
  }

  // Unsubscribe token from topic
  async unsubscribeFromTopic(tokens: string[], topic: string): Promise<boolean> {
    if (!this.isConfigured || !firebaseApp) {
      logger.warn('Cannot unsubscribe from topic - Firebase not configured');
      return false;
    }

    try {
      const response = await admin.messaging().unsubscribeFromTopic(tokens, topic);

      logger.info('Unsubscribed from topic', {
        topic,
        successCount: response.successCount,
        failureCount: response.failureCount,
      });

      return response.successCount > 0;
    } catch (error: any) {
      logger.error('Failed to unsubscribe from topic', {
        error: error.message,
        topic,
      });

      return false;
    }
  }

  // ========================================
  // PRE-BUILT NOTIFICATION TEMPLATES
  // ========================================

  // New job match notification
  async sendJobMatchNotification(
    tokens: string[],
    jobTitle: string,
    company: string,
    matchScore: number
  ): Promise<void> {
    const notification: PushNotification = {
      title: 'New Job Match!',
      body: `${matchScore}% match: ${jobTitle} at ${company}`,
      data: {
        type: 'job_match',
        jobTitle,
        company,
        matchScore: matchScore.toString(),
      },
      clickAction: `${process.env.FRONTEND_URL}/jobs`,
    };

    await this.sendToMultipleDevices(tokens, notification);
  }

  // Application status update notification
  async sendApplicationStatusNotification(
    tokens: string[],
    jobTitle: string,
    company: string,
    status: string
  ): Promise<void> {
    const statusMessages: Record<string, { title: string; body: string }> = {
      VIEWED: {
        title: 'Application Viewed!',
        body: `${company} viewed your application for ${jobTitle}`,
      },
      SCREENING: {
        title: 'Moving Forward!',
        body: `${company} is screening your application for ${jobTitle}`,
      },
      INTERVIEWING: {
        title: 'Interview Scheduled!',
        body: `Interview scheduled for ${jobTitle} at ${company}`,
      },
      OFFERED: {
        title: 'Congratulations!',
        body: `${company} made you an offer for ${jobTitle}!`,
      },
      REJECTED: {
        title: 'Application Update',
        body: `Update on ${jobTitle} at ${company}`,
      },
    };

    const message = statusMessages[status] || {
      title: 'Application Update',
      body: `Status changed to ${status} for ${jobTitle} at ${company}`,
    };

    const notification: PushNotification = {
      ...message,
      data: {
        type: 'application_status',
        jobTitle,
        company,
        status,
      },
      clickAction: `${process.env.FRONTEND_URL}/applications`,
    };

    await this.sendToMultipleDevices(tokens, notification);
  }

  // Interview reminder notification
  async sendInterviewReminderNotification(
    tokens: string[],
    jobTitle: string,
    company: string,
    interviewDate: Date
  ): Promise<void> {
    const timeUntil = this.getTimeUntilInterview(interviewDate);

    const notification: PushNotification = {
      title: 'Interview Reminder',
      body: `Your interview for ${jobTitle} at ${company} is ${timeUntil}`,
      data: {
        type: 'interview_reminder',
        jobTitle,
        company,
        interviewDate: interviewDate.toISOString(),
      },
      clickAction: `${process.env.FRONTEND_URL}/interview-prep`,
    };

    await this.sendToMultipleDevices(tokens, notification);
  }

  // Auto-application notification
  async sendAutoApplicationNotification(
    tokens: string[],
    jobTitle: string,
    company: string,
    success: boolean
  ): Promise<void> {
    const notification: PushNotification = {
      title: success ? 'Auto-Applied!' : 'Auto-Apply Failed',
      body: success
        ? `Successfully applied to ${jobTitle} at ${company}`
        : `Failed to apply to ${jobTitle} at ${company}. Manual application may be required.`,
      data: {
        type: 'auto_application',
        jobTitle,
        company,
        success: success.toString(),
      },
      clickAction: `${process.env.FRONTEND_URL}/applications`,
    };

    await this.sendToMultipleDevices(tokens, notification);
  }

  // Daily job digest notification
  async sendDailyJobDigestNotification(
    tokens: string[],
    newJobsCount: number,
    topJobTitle: string
  ): Promise<void> {
    const notification: PushNotification = {
      title: 'Daily Job Digest',
      body: `${newJobsCount} new jobs today! Top match: ${topJobTitle}`,
      data: {
        type: 'daily_digest',
        jobCount: newJobsCount.toString(),
        topJobTitle,
      },
      clickAction: `${process.env.FRONTEND_URL}/jobs`,
    };

    await this.sendToMultipleDevices(tokens, notification);
  }

  // Network connection notification
  async sendNetworkConnectionNotification(
    tokens: string[],
    contactName: string,
    contactTitle: string,
    company: string
  ): Promise<void> {
    const notification: PushNotification = {
      title: 'New Network Connection',
      body: `${contactName}, ${contactTitle} at ${company} accepted your connection request`,
      data: {
        type: 'network_connection',
        contactName,
        contactTitle,
        company,
      },
      clickAction: `${process.env.FRONTEND_URL}/networking`,
    };

    await this.sendToMultipleDevices(tokens, notification);
  }

  // ========================================
  // HELPER METHODS
  // ========================================

  private getTimeUntilInterview(interviewDate: Date): string {
    const now = new Date();
    const diff = interviewDate.getTime() - now.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours < 1) {
      return `in ${minutes} minutes`;
    } else if (hours < 24) {
      return `in ${hours} hours`;
    } else {
      const days = Math.floor(hours / 24);
      return `in ${days} day${days > 1 ? 's' : ''}`;
    }
  }
}

export const pushNotificationService = new PushNotificationService();
