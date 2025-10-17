import twilio from 'twilio';
import { logger } from '../config/logger';

// Initialize Twilio
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID || '';
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN || '';
const TWILIO_PHONE_NUMBER = process.env.TWILIO_PHONE_NUMBER || '';

let twilioClient: twilio.Twilio | null = null;

if (TWILIO_ACCOUNT_SID && TWILIO_AUTH_TOKEN) {
  twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);
}

export class SMSService {
  private isConfigured: boolean;

  constructor() {
    this.isConfigured = !!twilioClient && !!TWILIO_PHONE_NUMBER;
    if (!this.isConfigured) {
      logger.warn('Twilio not configured - SMS sending disabled');
    }
  }

  // Send SMS
  async sendSMS(to: string, message: string): Promise<boolean> {
    if (!this.isConfigured || !twilioClient) {
      logger.warn('Cannot send SMS - Twilio not configured', { to });
      return false;
    }

    try {
      // Ensure phone number is in E.164 format
      const formattedTo = this.formatPhoneNumber(to);

      const result = await twilioClient.messages.create({
        body: message,
        from: TWILIO_PHONE_NUMBER,
        to: formattedTo,
      });

      logger.info('SMS sent successfully', {
        to: formattedTo,
        sid: result.sid,
        status: result.status,
      });

      return true;
    } catch (error: any) {
      logger.error('Failed to send SMS', {
        error: error.message,
        to,
        code: error.code,
      });
      return false;
    }
  }

  // Send application status update SMS
  async sendApplicationStatusSMS(
    phone: string,
    jobTitle: string,
    company: string,
    status: string
  ): Promise<boolean> {
    const message = this.getApplicationStatusMessage(jobTitle, company, status);
    return this.sendSMS(phone, message);
  }

  // Send interview reminder SMS
  async sendInterviewReminderSMS(
    phone: string,
    jobTitle: string,
    company: string,
    interviewDate: Date
  ): Promise<boolean> {
    const dateStr = interviewDate.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
    const timeStr = interviewDate.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });

    const message = `Interview Reminder: ${jobTitle} at ${company} on ${dateStr} at ${timeStr}. Good luck! - JobRight Automation`;

    return this.sendSMS(phone, message);
  }

  // Send job match notification SMS
  async sendJobMatchSMS(
    phone: string,
    jobCount: number,
    topJobTitle: string
  ): Promise<boolean> {
    const message = `You have ${jobCount} new job matches! Top match: ${topJobTitle}. Check your dashboard at ${process.env.FRONTEND_URL}/jobs - JobRight Automation`;

    return this.sendSMS(phone, message);
  }

  // Send verification code SMS
  async sendVerificationCodeSMS(phone: string, code: string): Promise<boolean> {
    const message = `Your JobRight Automation verification code is: ${code}. This code expires in 10 minutes.`;

    return this.sendSMS(phone, message);
  }

  // Send MFA code SMS
  async sendMFACodeSMS(phone: string, code: string): Promise<boolean> {
    const message = `Your JobRight Automation login code is: ${code}. This code expires in 5 minutes.`;

    return this.sendSMS(phone, message);
  }

  // Send application auto-submitted SMS
  async sendAutoApplicationSMS(
    phone: string,
    jobTitle: string,
    company: string
  ): Promise<boolean> {
    const message = `Auto-applied to ${jobTitle} at ${company}! View status: ${process.env.FRONTEND_URL}/applications - JobRight Automation`;

    return this.sendSMS(phone, message);
  }

  // ========================================
  // HELPER METHODS
  // ========================================

  // Format phone number to E.164 format
  private formatPhoneNumber(phone: string): string {
    // Remove all non-digit characters
    let cleaned = phone.replace(/\D/g, '');

    // Add country code if not present
    if (cleaned.length === 10) {
      cleaned = '1' + cleaned; // Add US country code
    }

    // Add + prefix
    if (!cleaned.startsWith('+')) {
      cleaned = '+' + cleaned;
    }

    return cleaned;
  }

  // Get application status message
  private getApplicationStatusMessage(
    jobTitle: string,
    company: string,
    status: string
  ): string {
    const statusMessages: Record<string, string> = {
      VIEWED: `Great news! ${company} viewed your application for ${jobTitle}. - JobRight Automation`,
      SCREENING: `You're moving forward! ${company} is screening your application for ${jobTitle}. - JobRight Automation`,
      INTERVIEWING: `Interview scheduled for ${jobTitle} at ${company}! Check your email for details. - JobRight Automation`,
      OFFERED: `Congratulations! ${company} made you an offer for ${jobTitle}! - JobRight Automation`,
      REJECTED: `Update on ${jobTitle} at ${company}: They went with another candidate. Keep going! - JobRight Automation`,
    };

    return (
      statusMessages[status] ||
      `Application status update: ${status} for ${jobTitle} at ${company}. - JobRight Automation`
    );
  }

  // Validate phone number format
  isValidPhoneNumber(phone: string): boolean {
    // Remove all non-digit characters
    const cleaned = phone.replace(/\D/g, '');

    // Check if it's a valid length (10 digits for US, or 11 with country code)
    return cleaned.length === 10 || cleaned.length === 11;
  }
}

export const smsService = new SMSService();
