import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';
import { applicationQueue } from '../config/queues';

export class ApplicationService {
  async createApplication(
    userId: string,
    jobId: string,
    resumeId?: string,
    coverLetter?: string
  ) {
    try {
      const application = await prisma.application.create({
        data: {
          userId,
          jobId,
          resumeId,
          coverLetter,
          status: 'PENDING',
        },
        include: {
          job: true,
          resume: true,
        },
      });

      logger.info('Application created', { userId, applicationId: application.id, jobId });

      return application;
    } catch (error) {
      logger.error('Create application error', { error, userId, jobId });
      throw error;
    }
  }

  async getUserApplications(userId: string, filters?: {
    status?: string;
    page?: number;
    limit?: number;
  }) {
    try {
      const { status, page = 1, limit = 20 } = filters || {};
      const skip = (page - 1) * limit;

      const where: any = { userId };
      if (status) {
        where.status = status;
      }

      const [applications, total] = await Promise.all([
        prisma.application.findMany({
          where,
          skip,
          take: limit,
          include: {
            job: true,
            resume: true,
            interviews: true,
          },
          orderBy: { appliedAt: 'desc' },
        }),
        prisma.application.count({ where }),
      ]);

      return {
        applications,
        pagination: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit),
        },
      };
    } catch (error) {
      logger.error('Get user applications error', { error, userId });
      throw error;
    }
  }

  async getApplicationById(applicationId: string, userId: string) {
    try {
      const application = await prisma.application.findFirst({
        where: {
          id: applicationId,
          userId,
        },
        include: {
          job: true,
          resume: true,
          interviews: true,
        },
      });

      if (!application) {
        throw new AppError('Application not found', 404);
      }

      return application;
    } catch (error) {
      logger.error('Get application error', { error, applicationId });
      throw error;
    }
  }

  async updateApplicationStatus(
    applicationId: string,
    userId: string,
    status: string,
    notes?: string
  ) {
    try {
      const updateData: any = { status };

      // Update specific date fields based on status
      if (status === 'VIEWED') updateData.viewedAt = new Date();
      if (status === 'SCREENING') updateData.respondedAt = new Date();
      if (status === 'INTERVIEWING') updateData.interviewedAt = new Date();
      if (status === 'OFFERED') updateData.offeredAt = new Date();
      if (status === 'REJECTED') updateData.rejectedAt = new Date();

      if (notes) {
        updateData.notes = notes;
      }

      const application = await prisma.application.updateMany({
        where: {
          id: applicationId,
          userId,
        },
        data: updateData,
      });

      if (application.count === 0) {
        throw new AppError('Application not found', 404);
      }

      logger.info('Application status updated', { applicationId, userId, status });

      // Update analytics
      await this.updateUserAnalytics(userId);

      return application;
    } catch (error) {
      logger.error('Update application status error', { error, applicationId });
      throw error;
    }
  }

  async addCommunication(
    applicationId: string,
    userId: string,
    communication: {
      type: string;
      date: Date;
      from?: string;
      to?: string;
      subject?: string;
      message?: string;
    }
  ) {
    try {
      const application = await this.getApplicationById(applicationId, userId);

      const communications = Array.isArray(application.communications)
        ? [...application.communications, communication]
        : [communication];

      await prisma.application.update({
        where: { id: applicationId },
        data: { communications: communications as any },
      });

      logger.info('Communication added to application', { applicationId, userId });

      return communication;
    } catch (error) {
      logger.error('Add communication error', { error, applicationId });
      throw error;
    }
  }

  async scheduleInterview(
    applicationId: string,
    userId: string,
    interviewData: {
      type: string;
      scheduledAt: Date;
      duration?: number;
      location?: string;
      meetingLink?: string;
      interviewers?: string[];
    }
  ) {
    try {
      // Verify application belongs to user
      await this.getApplicationById(applicationId, userId);

      const interview = await prisma.interview.create({
        data: {
          applicationId,
          ...interviewData,
          status: 'SCHEDULED',
        },
      });

      // Update application status
      await this.updateApplicationStatus(applicationId, userId, 'INTERVIEWING');

      logger.info('Interview scheduled', { applicationId, userId, interviewId: interview.id });

      return interview;
    } catch (error) {
      logger.error('Schedule interview error', { error, applicationId });
      throw error;
    }
  }

  async submitAutoApplication(
    userId: string,
    jobId: string,
    resumeId: string,
    coverLetter?: string
  ) {
    try {
      // Create application record
      const application = await this.createApplication(userId, jobId, resumeId, coverLetter);

      // Queue auto-application job
      await applicationQueue.add('auto-apply', {
        applicationId: application.id,
        userId,
        jobId,
        resumeId,
        coverLetter,
      });

      logger.info('Auto-application queued', { applicationId: application.id, userId, jobId });

      return application;
    } catch (error) {
      logger.error('Submit auto-application error', { error, userId, jobId });
      throw error;
    }
  }

  async getApplicationStats(userId: string) {
    try {
      const [
        totalApplications,
        pending,
        submitted,
        viewed,
        screening,
        interviewing,
        offered,
        rejected,
      ] = await Promise.all([
        prisma.application.count({ where: { userId } }),
        prisma.application.count({ where: { userId, status: 'PENDING' } }),
        prisma.application.count({ where: { userId, status: 'SUBMITTED' } }),
        prisma.application.count({ where: { userId, status: 'VIEWED' } }),
        prisma.application.count({ where: { userId, status: 'SCREENING' } }),
        prisma.application.count({ where: { userId, status: 'INTERVIEWING' } }),
        prisma.application.count({ where: { userId, status: 'OFFERED' } }),
        prisma.application.count({ where: { userId, status: 'REJECTED' } }),
      ]);

      const responseRate = totalApplications > 0 ? ((viewed + screening + interviewing + offered) / totalApplications) * 100 : 0;
      const interviewRate = totalApplications > 0 ? ((interviewing + offered) / totalApplications) * 100 : 0;
      const offerRate = totalApplications > 0 ? (offered / totalApplications) * 100 : 0;

      return {
        totalApplications,
        byStatus: {
          pending,
          submitted,
          viewed,
          screening,
          interviewing,
          offered,
          rejected,
        },
        metrics: {
          responseRate: Math.round(responseRate),
          interviewRate: Math.round(interviewRate),
          offerRate: Math.round(offerRate),
        },
      };
    } catch (error) {
      logger.error('Get application stats error', { error, userId });
      throw error;
    }
  }

  private async updateUserAnalytics(userId: string) {
    try {
      const stats = await this.getApplicationStats(userId);

      await prisma.userAnalytics.upsert({
        where: { userId },
        update: {
          totalApplications: stats.totalApplications,
          totalResponses: stats.byStatus.viewed + stats.byStatus.screening + stats.byStatus.interviewing + stats.byStatus.offered,
          totalInterviews: stats.byStatus.interviewing + stats.byStatus.offered,
          totalOffers: stats.byStatus.offered,
          totalRejections: stats.byStatus.rejected,
          responseRate: stats.metrics.responseRate / 100,
          interviewRate: stats.metrics.interviewRate / 100,
          offerRate: stats.metrics.offerRate / 100,
        },
        create: {
          userId,
          totalApplications: stats.totalApplications,
          totalResponses: stats.byStatus.viewed + stats.byStatus.screening + stats.byStatus.interviewing + stats.byStatus.offered,
          totalInterviews: stats.byStatus.interviewing + stats.byStatus.offered,
          totalOffers: stats.byStatus.offered,
          totalRejections: stats.byStatus.rejected,
          responseRate: stats.metrics.responseRate / 100,
          interviewRate: stats.metrics.interviewRate / 100,
          offerRate: stats.metrics.offerRate / 100,
        },
      });
    } catch (error) {
      logger.error('Update user analytics error', { error, userId });
    }
  }
}

export const applicationService = new ApplicationService();
