import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';
import { cache } from '../config/redis';

interface JobSearchParams {
  query?: string;
  location?: string;
  jobType?: string[];
  workArrangement?: string[];
  minSalary?: number;
  maxSalary?: number;
  visaSponsorship?: boolean;
  page?: number;
  limit?: number;
}

interface JobMatchScore {
  jobId: string;
  score: number;
  reasons: string[];
}

export class JobService {
  async searchJobs(params: JobSearchParams, userId?: string) {
    try {
      const {
        query,
        location,
        jobType,
        workArrangement,
        minSalary,
        maxSalary,
        visaSponsorship,
        page = 1,
        limit = 20,
      } = params;

      const skip = (page - 1) * limit;

      const where: any = {
        status: 'ACTIVE',
      };

      if (query) {
        where.OR = [
          { title: { contains: query, mode: 'insensitive' } },
          { company: { contains: query, mode: 'insensitive' } },
          { description: { contains: query, mode: 'insensitive' } },
        ];
      }

      if (location) {
        where.location = { contains: location, mode: 'insensitive' };
      }

      if (jobType && jobType.length > 0) {
        where.jobType = { in: jobType };
      }

      if (workArrangement && workArrangement.length > 0) {
        where.workArrangement = { in: workArrangement };
      }

      if (minSalary !== undefined) {
        where.salaryMin = { gte: minSalary };
      }

      if (maxSalary !== undefined) {
        where.salaryMax = { lte: maxSalary };
      }

      if (visaSponsorship !== undefined) {
        where.visaSponsorship = visaSponsorship;
      }

      const [jobs, total] = await Promise.all([
        prisma.job.findMany({
          where,
          skip,
          take: limit,
          orderBy: { postedAt: 'desc' },
        }),
        prisma.job.count({ where }),
      ]);

      logger.info('Job search executed', {
        userId,
        params,
        resultsCount: jobs.length,
        totalCount: total,
      });

      return {
        jobs,
        pagination: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit),
        },
      };
    } catch (error) {
      logger.error('Job search error', { error, params });
      throw error;
    }
  }

  async getJobById(jobId: string, userId?: string) {
    try {
      const job = await prisma.job.findUnique({
        where: { id: jobId },
      });

      if (!job) {
        throw new AppError('Job not found', 404);
      }

      // Increment view count
      await prisma.job.update({
        where: { id: jobId },
        data: { viewCount: { increment: 1 } },
      });

      logger.info('Job viewed', { jobId, userId });

      return job;
    } catch (error) {
      logger.error('Get job error', { error, jobId });
      throw error;
    }
  }

  async getRecommendations(userId: string, limit: number = 20) {
    try {
      // Get user preferences and profile
      const [preferences, profile] = await Promise.all([
        prisma.preferences.findUnique({ where: { userId } }),
        prisma.profile.findUnique({ where: { userId } }),
      ]);

      if (!preferences) {
        throw new AppError('User preferences not found', 404);
      }

      // Check cache
      const cacheKey = `job:recommendations:${userId}`;
      const cached = await cache.get<any[]>(cacheKey);
      if (cached) {
        return cached.slice(0, limit);
      }

      // Build query based on preferences
      const where: any = {
        status: 'ACTIVE',
      };

      if (preferences.desiredRoles && preferences.desiredRoles.length > 0) {
        where.OR = preferences.desiredRoles.map((role) => ({
          title: { contains: role, mode: 'insensitive' },
        }));
      }

      if (preferences.desiredLocations && preferences.desiredLocations.length > 0) {
        where.location = { in: preferences.desiredLocations };
      }

      if (preferences.jobTypes && preferences.jobTypes.length > 0) {
        where.jobType = { in: preferences.jobTypes };
      }

      if (preferences.workArrangement && preferences.workArrangement.length > 0) {
        where.workArrangement = { in: preferences.workArrangement };
      }

      if (preferences.minSalary) {
        where.salaryMin = { gte: preferences.minSalary };
      }

      const jobs = await prisma.job.findMany({
        where,
        take: limit * 2, // Get more for scoring
        orderBy: { postedAt: 'desc' },
      });

      // Calculate match scores
      const scoredJobs = jobs.map((job) => ({
        ...job,
        matchScore: this.calculateMatchScore(job, preferences, profile),
      }));

      // Sort by match score and limit
      const recommendations = scoredJobs
        .sort((a, b) => b.matchScore - a.matchScore)
        .slice(0, limit);

      // Cache for 1 hour
      await cache.set(cacheKey, recommendations, 3600);

      logger.info('Recommendations generated', { userId, count: recommendations.length });

      return recommendations;
    } catch (error) {
      logger.error('Get recommendations error', { error, userId });
      throw error;
    }
  }

  async saveJob(userId: string, jobId: string, notes?: string) {
    try {
      const savedJob = await prisma.savedJob.create({
        data: {
          userId,
          jobId,
          notes,
        },
        include: {
          job: true,
        },
      });

      logger.info('Job saved', { userId, jobId });

      return savedJob;
    } catch (error) {
      logger.error('Save job error', { error, userId, jobId });
      throw error;
    }
  }

  async unsaveJob(userId: string, jobId: string) {
    try {
      await prisma.savedJob.delete({
        where: {
          userId_jobId: {
            userId,
            jobId,
          },
        },
      });

      logger.info('Job unsaved', { userId, jobId });

      return { message: 'Job unsaved successfully' };
    } catch (error) {
      logger.error('Unsave job error', { error, userId, jobId });
      throw error;
    }
  }

  async getSavedJobs(userId: string) {
    try {
      const savedJobs = await prisma.savedJob.findMany({
        where: { userId },
        include: {
          job: true,
        },
        orderBy: { createdAt: 'desc' },
      });

      return savedJobs;
    } catch (error) {
      logger.error('Get saved jobs error', { error, userId });
      throw error;
    }
  }

  private calculateMatchScore(job: any, preferences: any, profile: any): number {
    let score = 0;
    const maxScore = 100;

    // Title match (30 points)
    if (preferences.desiredRoles && preferences.desiredRoles.length > 0) {
      const titleMatch = preferences.desiredRoles.some((role: string) =>
        job.title.toLowerCase().includes(role.toLowerCase())
      );
      if (titleMatch) score += 30;
    }

    // Location match (20 points)
    if (preferences.desiredLocations && preferences.desiredLocations.length > 0) {
      const locationMatch = preferences.desiredLocations.some((loc: string) =>
        job.location.toLowerCase().includes(loc.toLowerCase())
      );
      if (locationMatch) score += 20;
    }

    // Job type match (15 points)
    if (preferences.jobTypes && preferences.jobTypes.includes(job.jobType)) {
      score += 15;
    }

    // Work arrangement match (15 points)
    if (preferences.workArrangement && preferences.workArrangement.includes(job.workArrangement)) {
      score += 15;
    }

    // Salary match (20 points)
    if (job.salaryMin && job.salaryMax && preferences.minSalary) {
      if (job.salaryMax >= preferences.minSalary) {
        score += 20;
      }
    }

    return Math.min(score, maxScore);
  }
}

export const jobService = new JobService();
