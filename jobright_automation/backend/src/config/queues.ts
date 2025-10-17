import Queue from 'bull';
import { logger } from './logger';

const redisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD || undefined,
};

// Create queues
export const jobSearchQueue = new Queue('job-search', { redis: redisConfig });
export const applicationQueue = new Queue('application', { redis: redisConfig });
export const resumeQueue = new Queue('resume', { redis: redisConfig });
export const emailQueue = new Queue('email', { redis: redisConfig });
export const notificationQueue = new Queue('notification', { redis: redisConfig });
export const analyticsQueue = new Queue('analytics', { redis: redisConfig });
export const scraperQueue = new Queue('scraper', { redis: redisConfig });

// Queue event handlers
const setupQueueEvents = (queue: Queue.Queue, name: string) => {
  queue.on('completed', (job) => {
    logger.info(`${name} job completed`, { jobId: job.id });
  });

  queue.on('failed', (job, err) => {
    logger.error(`${name} job failed`, { jobId: job?.id, error: err });
  });

  queue.on('error', (error) => {
    logger.error(`${name} queue error`, { error });
  });
};

export async function initializeQueues() {
  try {
    // Set up event handlers
    setupQueueEvents(jobSearchQueue, 'Job Search');
    setupQueueEvents(applicationQueue, 'Application');
    setupQueueEvents(resumeQueue, 'Resume');
    setupQueueEvents(emailQueue, 'Email');
    setupQueueEvents(notificationQueue, 'Notification');
    setupQueueEvents(analyticsQueue, 'Analytics');
    setupQueueEvents(scraperQueue, 'Scraper');

    logger.info('All queues initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize queues', { error });
    throw error;
  }
}

// Job processing will be implemented in workers
export const queues = {
  jobSearch: jobSearchQueue,
  application: applicationQueue,
  resume: resumeQueue,
  email: emailQueue,
  notification: notificationQueue,
  analytics: analyticsQueue,
  scraper: scraperQueue,
};
