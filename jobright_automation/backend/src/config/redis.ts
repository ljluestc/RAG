import Redis from 'ioredis';
import { logger } from './logger';

const redisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD || undefined,
  db: parseInt(process.env.REDIS_DB || '0'),
  retryStrategy: (times: number) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
};

const redis = new Redis(redisConfig);

redis.on('connect', () => {
  logger.info('Redis connection established');
});

redis.on('error', (error) => {
  logger.error('Redis connection error', { error });
});

redis.on('close', () => {
  logger.info('Redis connection closed');
});

export async function connectRedis() {
  try {
    await redis.ping();
    return redis;
  } catch (error) {
    logger.error('Failed to connect to Redis', { error });
    throw error;
  }
}

export async function disconnectRedis() {
  try {
    await redis.quit();
    logger.info('Redis disconnected');
  } catch (error) {
    logger.error('Error disconnecting from Redis', { error });
  }
}

// Cache utilities
export const cache = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const data = await redis.get(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      logger.error('Cache get error', { key, error });
      return null;
    }
  },

  async set(key: string, value: any, ttl?: number): Promise<boolean> {
    try {
      const data = JSON.stringify(value);
      if (ttl) {
        await redis.setex(key, ttl, data);
      } else {
        await redis.set(key, data);
      }
      return true;
    } catch (error) {
      logger.error('Cache set error', { key, error });
      return false;
    }
  },

  async del(key: string): Promise<boolean> {
    try {
      await redis.del(key);
      return true;
    } catch (error) {
      logger.error('Cache delete error', { key, error });
      return false;
    }
  },

  async keys(pattern: string): Promise<string[]> {
    try {
      return await redis.keys(pattern);
    } catch (error) {
      logger.error('Cache keys error', { pattern, error });
      return [];
    }
  },

  async flush(): Promise<boolean> {
    try {
      await redis.flushdb();
      return true;
    } catch (error) {
      logger.error('Cache flush error', { error });
      return false;
    }
  },
};

export { redis };
