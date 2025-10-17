import { PrismaClient } from '@prisma/client';
import { logger } from './logger';

const prisma = new PrismaClient({
  log: [
    { level: 'warn', emit: 'event' },
    { level: 'error', emit: 'event' },
  ],
});

// Log database queries in development
if (process.env.NODE_ENV === 'development') {
  prisma.$on('query' as never, (e: any) => {
    logger.debug('Database Query', {
      query: e.query,
      params: e.params,
      duration: `${e.duration}ms`,
    });
  });
}

// Log warnings and errors
prisma.$on('warn' as never, (e: any) => {
  logger.warn('Database Warning', { message: e.message });
});

prisma.$on('error' as never, (e: any) => {
  logger.error('Database Error', { message: e.message });
});

export async function connectDatabase() {
  try {
    await prisma.$connect();
    logger.info('Database connection established');
    return prisma;
  } catch (error) {
    logger.error('Failed to connect to database', { error });
    throw error;
  }
}

export async function disconnectDatabase() {
  try {
    await prisma.$disconnect();
    logger.info('Database connection closed');
  } catch (error) {
    logger.error('Error disconnecting from database', { error });
    throw error;
  }
}

export { prisma };
