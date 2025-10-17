import express, { Application } from 'express';
import dotenv from 'dotenv';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import cookieParser from 'cookie-parser';
import { createServer } from 'http';
import { Server } from 'ws';

// Load environment variables
dotenv.config();

// Import configurations
import { logger } from './config/logger';
import { connectDatabase } from './config/database';
import { connectRedis } from './config/redis';
import { initializeQueues } from './config/queues';

// Import routes
import authRoutes from './controllers/auth.controller';
import userRoutes from './controllers/user.controller';
import jobRoutes from './controllers/job.controller';
import applicationRoutes from './controllers/application.controller';
import resumeRoutes from './controllers/resume.controller';
import copilotRoutes from './controllers/copilot.controller';
import networkingRoutes from './controllers/networking.controller';
import analyticsRoutes from './controllers/analytics.controller';
import notificationRoutes from './controllers/notification.controller';
import subscriptionRoutes from './controllers/subscription.controller';
import webhookRoutes from './routes/webhook.routes';

// Import middleware
import { errorHandler } from './middleware/error.middleware';
import { requestLogger } from './middleware/logger.middleware';
import { rateLimiter } from './middleware/rateLimit.middleware';

const app: Application = express();
const PORT = process.env.PORT || 3000;
const API_VERSION = process.env.API_VERSION || 'v1';

// ========================================
// MIDDLEWARE
// ========================================

// Security
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN?.split(',') || '*',
  credentials: true,
}));

// Webhook routes (must come before body parsing for Stripe signature verification)
app.use('/webhooks', express.raw({ type: 'application/json' }), webhookRoutes);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(cookieParser());

// Compression
app.use(compression());

// Logging
app.use(requestLogger);

// Rate limiting
app.use(rateLimiter);

// ========================================
// ROUTES
// ========================================

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// API Routes
const apiPrefix = `/api/${API_VERSION}`;

app.use(`${apiPrefix}/auth`, authRoutes);
app.use(`${apiPrefix}/users`, userRoutes);
app.use(`${apiPrefix}/jobs`, jobRoutes);
app.use(`${apiPrefix}/applications`, applicationRoutes);
app.use(`${apiPrefix}/resumes`, resumeRoutes);
app.use(`${apiPrefix}/copilot`, copilotRoutes);
app.use(`${apiPrefix}/networking`, networkingRoutes);
app.use(`${apiPrefix}/analytics`, analyticsRoutes);
app.use(`${apiPrefix}/notifications`, notificationRoutes);
app.use(`${apiPrefix}/subscriptions`, subscriptionRoutes);

// Error handling
app.use(errorHandler);

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// ========================================
// WEBSOCKET SERVER
// ========================================

const server = createServer(app);
const wss = new Server({ server, path: '/ws' });

wss.on('connection', (ws, req) => {
  logger.info('WebSocket client connected');

  ws.on('message', (message: string) => {
    try {
      const data = JSON.parse(message.toString());
      // Handle WebSocket messages (real-time copilot, notifications, etc.)
      logger.debug('WebSocket message received', { data });
    } catch (error) {
      logger.error('WebSocket message parsing error', { error });
    }
  });

  ws.on('close', () => {
    logger.info('WebSocket client disconnected');
  });

  ws.on('error', (error) => {
    logger.error('WebSocket error', { error });
  });
});

// ========================================
// INITIALIZATION & STARTUP
// ========================================

async function startServer() {
  try {
    // Connect to database
    await connectDatabase();
    logger.info('Database connected successfully');

    // Connect to Redis
    await connectRedis();
    logger.info('Redis connected successfully');

    // Initialize job queues
    await initializeQueues();
    logger.info('Job queues initialized successfully');

    // Start server
    server.listen(PORT, () => {
      logger.info(`Server started on port ${PORT}`);
      logger.info(`API available at http://localhost:${PORT}${apiPrefix}`);
      logger.info(`WebSocket available at ws://localhost:${PORT}/ws`);
    });
  } catch (error) {
    logger.error('Failed to start server', { error });
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully...');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully...');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
});

// Start the server
startServer();

export { app, wss };
