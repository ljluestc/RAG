import { Router } from 'express';
import { webhookController } from '../controllers/webhook.controller';

const router = Router();

// Stripe webhook endpoint
// Note: This route must use raw body, not JSON parsed body
router.post(
  '/stripe',
  webhookController.handleStripeWebhook.bind(webhookController)
);

export default router;
