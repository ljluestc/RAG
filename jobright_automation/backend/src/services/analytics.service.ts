import { prisma } from '../config/database';
import { logger } from '../config/logger';

export class AnalyticsService {
  async getDashboardStats(userId: string) {
    try {
      const [
        totalApplications,
        applications,
        savedJobs,
        resumes,
        connections,
        analytics,
      ] = await Promise.all([
        prisma.application.count({ where: { userId } }),
        prisma.application.findMany({
          where: { userId },
          select: { status: true, appliedAt: true },
        }),
        prisma.savedJob.count({ where: { userId } }),
        prisma.resume.count({ where: { userId } }),
        prisma.connection.count({ where: { userId } }),
        prisma.userAnalytics.findUnique({ where: { userId } }),
      ]);

      // Calculate stats
      const last7Days = applications.filter(
        (app) => app.appliedAt > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      ).length;

      const last30Days = applications.filter(
        (app) => app.appliedAt > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      ).length;

      const statusCounts = applications.reduce((acc: any, app) => {
        acc[app.status] = (acc[app.status] || 0) + 1;
        return acc;
      }, {});

      return {
        overview: {
          totalApplications,
          savedJobs,
          resumes,
          connections,
          applicationsLast7Days: last7Days,
          applicationsLast30Days: last30Days,
        },
        applicationsByStatus: statusCounts,
        metrics: {
          responseRate: analytics?.responseRate || 0,
          interviewRate: analytics?.interviewRate || 0,
          offerRate: analytics?.offerRate || 0,
        },
      };
    } catch (error) {
      logger.error('Get dashboard stats error', { error, userId });
      throw error;
    }
  }

  async getApplicationTrends(userId: string, days: number = 30) {
    try {
      const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

      const applications = await prisma.application.findMany({
        where: {
          userId,
          appliedAt: { gte: startDate },
        },
        select: {
          appliedAt: true,
          status: true,
        },
        orderBy: { appliedAt: 'asc' },
      });

      // Group by date
      const trendData = applications.reduce((acc: any, app) => {
        const date = app.appliedAt.toISOString().split('T')[0];
        if (!acc[date]) {
          acc[date] = { date, count: 0, statuses: {} };
        }
        acc[date].count++;
        acc[date].statuses[app.status] = (acc[date].statuses[app.status] || 0) + 1;
        return acc;
      }, {});

      return Object.values(trendData);
    } catch (error) {
      logger.error('Get application trends error', { error, userId });
      throw error;
    }
  }

  async getJobSearchAnalytics(userId: string) {
    try {
      const analytics = await prisma.userAnalytics.findUnique({
        where: { userId },
      });

      if (!analytics) {
        return {
          totalSearches: 0,
          totalJobsViewed: 0,
          totalJobsSaved: 0,
        };
      }

      return {
        totalSearches: analytics.totalSearches,
        totalJobsViewed: analytics.totalJobsViewed,
        totalJobsSaved: analytics.totalJobsSaved,
      };
    } catch (error) {
      logger.error('Get job search analytics error', { error, userId });
      throw error;
    }
  }

  async getConversionFunnel(userId: string) {
    try {
      const analytics = await prisma.userAnalytics.findUnique({
        where: { userId },
      });

      if (!analytics) {
        return {
          applications: 0,
          responses: 0,
          interviews: 0,
          offers: 0,
        };
      }

      return {
        applications: analytics.totalApplications,
        responses: analytics.totalResponses,
        interviews: analytics.totalInterviews,
        offers: analytics.totalOffers,
        rejections: analytics.totalRejections,
      };
    } catch (error) {
      logger.error('Get conversion funnel error', { error, userId });
      throw error;
    }
  }

  async generateReport(userId: string, reportType: string) {
    try {
      const stats = await this.getDashboardStats(userId);
      const trends = await this.getApplicationTrends(userId);
      const funnel = await this.getConversionFunnel(userId);

      const report = {
        generatedAt: new Date(),
        userId,
        reportType,
        stats,
        trends,
        funnel,
      };

      logger.info('Report generated', { userId, reportType });

      return report;
    } catch (error) {
      logger.error('Generate report error', { error, userId });
      throw error;
    }
  }
}

export const analyticsService = new AnalyticsService();
