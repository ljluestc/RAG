import sgMail from '@sendgrid/mail';
import { logger } from '../config/logger';

// Initialize SendGrid
const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY || '';
if (SENDGRID_API_KEY) {
  sgMail.setApiKey(SENDGRID_API_KEY);
}

const FROM_EMAIL = process.env.FROM_EMAIL || 'noreply@jobright-automation.com';
const FROM_NAME = process.env.FROM_NAME || 'JobRight Automation';

export interface EmailTemplate {
  to: string;
  subject: string;
  html: string;
  text?: string;
}

export class EmailService {
  private isConfigured: boolean;

  constructor() {
    this.isConfigured = !!SENDGRID_API_KEY;
    if (!this.isConfigured) {
      logger.warn('SendGrid API key not configured - email sending disabled');
    }
  }

  // Send email
  async sendEmail(template: EmailTemplate): Promise<boolean> {
    if (!this.isConfigured) {
      logger.warn('Cannot send email - SendGrid not configured', { to: template.to });
      return false;
    }

    try {
      await sgMail.send({
        to: template.to,
        from: {
          email: FROM_EMAIL,
          name: FROM_NAME,
        },
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      logger.info('Email sent successfully', { to: template.to, subject: template.subject });
      return true;
    } catch (error: any) {
      logger.error('Failed to send email', {
        error: error.message,
        to: template.to,
        subject: template.subject,
      });
      return false;
    }
  }

  // Welcome email
  async sendWelcomeEmail(email: string, name: string): Promise<boolean> {
    const template: EmailTemplate = {
      to: email,
      subject: 'Welcome to JobRight Automation!',
      html: this.getWelcomeEmailHTML(name),
      text: this.getWelcomeEmailText(name),
    };

    return this.sendEmail(template);
  }

  // Password reset email
  async sendPasswordResetEmail(email: string, resetToken: string): Promise<boolean> {
    const resetUrl = `${process.env.FRONTEND_URL}/reset-password?token=${resetToken}`;

    const template: EmailTemplate = {
      to: email,
      subject: 'Reset Your Password',
      html: this.getPasswordResetEmailHTML(resetUrl),
      text: this.getPasswordResetEmailText(resetUrl),
    };

    return this.sendEmail(template);
  }

  // Email verification
  async sendVerificationEmail(email: string, verificationToken: string): Promise<boolean> {
    const verifyUrl = `${process.env.FRONTEND_URL}/verify-email?token=${verificationToken}`;

    const template: EmailTemplate = {
      to: email,
      subject: 'Verify Your Email Address',
      html: this.getVerificationEmailHTML(verifyUrl),
      text: this.getVerificationEmailText(verifyUrl),
    };

    return this.sendEmail(template);
  }

  // Application submitted notification
  async sendApplicationSubmittedEmail(
    email: string,
    jobTitle: string,
    company: string
  ): Promise<boolean> {
    const template: EmailTemplate = {
      to: email,
      subject: `Application Submitted: ${jobTitle} at ${company}`,
      html: this.getApplicationSubmittedEmailHTML(jobTitle, company),
      text: this.getApplicationSubmittedEmailText(jobTitle, company),
    };

    return this.sendEmail(template);
  }

  // Job recommendations email
  async sendJobRecommendationsEmail(
    email: string,
    name: string,
    jobs: Array<{ title: string; company: string; location: string; url: string }>
  ): Promise<boolean> {
    const template: EmailTemplate = {
      to: email,
      subject: `${jobs.length} New Job Recommendations for You`,
      html: this.getJobRecommendationsEmailHTML(name, jobs),
      text: this.getJobRecommendationsEmailText(name, jobs),
    };

    return this.sendEmail(template);
  }

  // Interview reminder email
  async sendInterviewReminderEmail(
    email: string,
    jobTitle: string,
    company: string,
    interviewDate: Date,
    interviewType: string
  ): Promise<boolean> {
    const template: EmailTemplate = {
      to: email,
      subject: `Interview Reminder: ${jobTitle} at ${company}`,
      html: this.getInterviewReminderEmailHTML(jobTitle, company, interviewDate, interviewType),
      text: this.getInterviewReminderEmailText(jobTitle, company, interviewDate, interviewType),
    };

    return this.sendEmail(template);
  }

  // Subscription confirmation email
  async sendSubscriptionConfirmationEmail(
    email: string,
    tier: string,
    amount: number
  ): Promise<boolean> {
    const template: EmailTemplate = {
      to: email,
      subject: `Subscription Confirmed: ${tier} Plan`,
      html: this.getSubscriptionConfirmationEmailHTML(tier, amount),
      text: this.getSubscriptionConfirmationEmailText(tier, amount),
    };

    return this.sendEmail(template);
  }

  // ========================================
  // HTML TEMPLATES
  // ========================================

  private getWelcomeEmailHTML(name: string): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
          .footer { text-align: center; margin-top: 30px; color: #777; font-size: 14px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Welcome to JobRight Automation!</h1>
          </div>
          <div class="content">
            <p>Hi ${name},</p>
            <p>Thank you for joining JobRight Automation! We're excited to help you accelerate your job search with AI-powered automation.</p>
            <p>Here's what you can do with your account:</p>
            <ul>
              <li><strong>AI Job Matching:</strong> Get personalized job recommendations based on your profile</li>
              <li><strong>Auto-Apply:</strong> Automatically apply to jobs with one click</li>
              <li><strong>Resume Optimization:</strong> Let our AI optimize your resume for each job</li>
              <li><strong>Interview Prep:</strong> Get AI-generated interview questions and tips</li>
              <li><strong>Application Tracking:</strong> Track all your applications in one place</li>
            </ul>
            <a href="${process.env.FRONTEND_URL}/dashboard" class="button">Get Started</a>
            <p>If you have any questions, feel free to reach out to our support team.</p>
            <p>Happy job hunting!</p>
            <p>The JobRight Automation Team</p>
          </div>
          <div class="footer">
            <p>&copy; ${new Date().getFullYear()} JobRight Automation. All rights reserved.</p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getPasswordResetEmailHTML(resetUrl: string): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: #667eea; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
          .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Reset Your Password</h1>
          </div>
          <div class="content">
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <a href="${resetUrl}" class="button">Reset Password</a>
            <div class="warning">
              <p><strong>Security Notice:</strong> This link will expire in 1 hour. If you didn't request this reset, you can safely ignore this email.</p>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #667eea;">${resetUrl}</p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getVerificationEmailHTML(verifyUrl: string): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: #667eea; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Verify Your Email</h1>
          </div>
          <div class="content">
            <p>Thank you for signing up! Please verify your email address to activate your account:</p>
            <a href="${verifyUrl}" class="button">Verify Email</a>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #667eea;">${verifyUrl}</p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getApplicationSubmittedEmailHTML(jobTitle: string, company: string): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: #28a745; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
          .success { background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>✓ Application Submitted!</h1>
          </div>
          <div class="content">
            <div class="success">
              <p><strong>Your application has been successfully submitted!</strong></p>
            </div>
            <p><strong>Position:</strong> ${jobTitle}</p>
            <p><strong>Company:</strong> ${company}</p>
            <p>We'll notify you as soon as there's an update on your application.</p>
            <p><a href="${process.env.FRONTEND_URL}/applications">View Application Status</a></p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getJobRecommendationsEmailHTML(
    name: string,
    jobs: Array<{ title: string; company: string; location: string; url: string }>
  ): string {
    const jobListHTML = jobs
      .map(
        (job) => `
      <div style="border: 1px solid #ddd; padding: 20px; margin: 15px 0; border-radius: 8px; background: white;">
        <h3 style="margin: 0 0 10px 0; color: #667eea;">${job.title}</h3>
        <p style="margin: 5px 0;"><strong>${job.company}</strong> • ${job.location}</p>
        <a href="${job.url}" style="display: inline-block; padding: 8px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px;">View Job</a>
      </div>
    `
      )
      .join('');

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>New Job Recommendations</h1>
          </div>
          <div class="content">
            <p>Hi ${name},</p>
            <p>We found ${jobs.length} new jobs that match your profile!</p>
            ${jobListHTML}
            <p><a href="${process.env.FRONTEND_URL}/jobs">View All Recommendations</a></p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getInterviewReminderEmailHTML(
    jobTitle: string,
    company: string,
    interviewDate: Date,
    interviewType: string
  ): string {
    const dateStr = interviewDate.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    const timeStr = interviewDate.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: #ffc107; color: #333; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
          .reminder { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>⏰ Interview Reminder</h1>
          </div>
          <div class="content">
            <div class="reminder">
              <p><strong>Your interview is coming up!</strong></p>
            </div>
            <p><strong>Position:</strong> ${jobTitle}</p>
            <p><strong>Company:</strong> ${company}</p>
            <p><strong>Interview Type:</strong> ${interviewType}</p>
            <p><strong>Date:</strong> ${dateStr}</p>
            <p><strong>Time:</strong> ${timeStr}</p>
            <p><a href="${process.env.FRONTEND_URL}/interview-prep">Prepare for Your Interview</a></p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getSubscriptionConfirmationEmailHTML(tier: string, amount: number): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: #28a745; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Subscription Confirmed!</h1>
          </div>
          <div class="content">
            <p>Thank you for subscribing to the <strong>${tier} Plan</strong>!</p>
            <p><strong>Amount:</strong> $${amount.toFixed(2)}/month</p>
            <p>You now have access to all premium features. Start using them today!</p>
            <p><a href="${process.env.FRONTEND_URL}/dashboard">Go to Dashboard</a></p>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  // ========================================
  // TEXT TEMPLATES (for email clients that don't support HTML)
  // ========================================

  private getWelcomeEmailText(name: string): string {
    return `
Welcome to JobRight Automation!

Hi ${name},

Thank you for joining JobRight Automation! We're excited to help you accelerate your job search with AI-powered automation.

Here's what you can do with your account:
- AI Job Matching: Get personalized job recommendations
- Auto-Apply: Automatically apply to jobs with one click
- Resume Optimization: Let our AI optimize your resume
- Interview Prep: Get AI-generated interview questions
- Application Tracking: Track all your applications

Get started: ${process.env.FRONTEND_URL}/dashboard

The JobRight Automation Team
    `.trim();
  }

  private getPasswordResetEmailText(resetUrl: string): string {
    return `
Reset Your Password

We received a request to reset your password. Visit the link below to create a new password:

${resetUrl}

This link will expire in 1 hour. If you didn't request this reset, you can safely ignore this email.
    `.trim();
  }

  private getVerificationEmailText(verifyUrl: string): string {
    return `
Verify Your Email

Thank you for signing up! Please verify your email address to activate your account:

${verifyUrl}
    `.trim();
  }

  private getApplicationSubmittedEmailText(jobTitle: string, company: string): string {
    return `
Application Submitted!

Your application has been successfully submitted!

Position: ${jobTitle}
Company: ${company}

We'll notify you as soon as there's an update on your application.

View application status: ${process.env.FRONTEND_URL}/applications
    `.trim();
  }

  private getJobRecommendationsEmailText(
    name: string,
    jobs: Array<{ title: string; company: string; location: string; url: string }>
  ): string {
    const jobList = jobs
      .map((job, i) => `\n${i + 1}. ${job.title} at ${job.company} (${job.location})\n   ${job.url}`)
      .join('\n');

    return `
New Job Recommendations

Hi ${name},

We found ${jobs.length} new jobs that match your profile!
${jobList}

View all recommendations: ${process.env.FRONTEND_URL}/jobs
    `.trim();
  }

  private getInterviewReminderEmailText(
    jobTitle: string,
    company: string,
    interviewDate: Date,
    interviewType: string
  ): string {
    return `
Interview Reminder

Your interview is coming up!

Position: ${jobTitle}
Company: ${company}
Interview Type: ${interviewType}
Date: ${interviewDate.toLocaleDateString()}
Time: ${interviewDate.toLocaleTimeString()}

Prepare for your interview: ${process.env.FRONTEND_URL}/interview-prep
    `.trim();
  }

  private getSubscriptionConfirmationEmailText(tier: string, amount: number): string {
    return `
Subscription Confirmed!

Thank you for subscribing to the ${tier} Plan!

Amount: $${amount.toFixed(2)}/month

You now have access to all premium features.

Go to dashboard: ${process.env.FRONTEND_URL}/dashboard
    `.trim();
  }
}

export const emailService = new EmailService();
