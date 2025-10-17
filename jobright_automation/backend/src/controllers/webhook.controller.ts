import { Request, Response } from 'express';
import Stripe from 'stripe';
import { logger } from '../config/logger';
import { prisma } from '../config/database';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2024-12-18.acacia',
});

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;

export class WebhookController {
  // Handle Stripe webhooks
  async handleStripeWebhook(req: Request, res: Response) {
    const sig = req.headers['stripe-signature'] as string;

    let event: Stripe.Event;

    try {
      // Verify webhook signature
      event = stripe.webhooks.constructEvent(
        req.body,
        sig,
        webhookSecret
      );
    } catch (err: any) {
      logger.error('Webhook signature verification failed', { error: err.message });
      return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    logger.info('Stripe webhook received', { type: event.type, id: event.id });

    try {
      // Handle the event
      switch (event.type) {
        case 'customer.subscription.created':
          await this.handleSubscriptionCreated(event.data.object as Stripe.Subscription);
          break;

        case 'customer.subscription.updated':
          await this.handleSubscriptionUpdated(event.data.object as Stripe.Subscription);
          break;

        case 'customer.subscription.deleted':
          await this.handleSubscriptionDeleted(event.data.object as Stripe.Subscription);
          break;

        case 'invoice.payment_succeeded':
          await this.handlePaymentSucceeded(event.data.object as Stripe.Invoice);
          break;

        case 'invoice.payment_failed':
          await this.handlePaymentFailed(event.data.object as Stripe.Invoice);
          break;

        case 'checkout.session.completed':
          await this.handleCheckoutCompleted(event.data.object as Stripe.Checkout.Session);
          break;

        default:
          logger.warn('Unhandled webhook event type', { type: event.type });
      }

      res.json({ received: true });
    } catch (error: any) {
      logger.error('Error processing webhook', { error: error.message, type: event.type });
      res.status(500).json({ error: 'Webhook processing failed' });
    }
  }

  // Handle subscription created
  private async handleSubscriptionCreated(subscription: Stripe.Subscription) {
    const customerId = subscription.customer as string;
    const priceId = subscription.items.data[0]?.price.id;

    // Find user by Stripe customer ID
    const user = await prisma.user.findFirst({
      where: { stripeCustomerId: customerId },
    });

    if (!user) {
      logger.error('User not found for Stripe customer', { customerId });
      return;
    }

    // Determine subscription tier
    const tier = this.getTierFromPriceId(priceId);

    // Update user subscription
    await prisma.user.update({
      where: { id: user.id },
      data: {
        subscriptionTier: tier,
        stripeSubscriptionId: subscription.id,
        subscriptionStatus: subscription.status,
      },
    });

    logger.info('Subscription created', { userId: user.id, tier, subscriptionId: subscription.id });
  }

  // Handle subscription updated
  private async handleSubscriptionUpdated(subscription: Stripe.Subscription) {
    const user = await prisma.user.findFirst({
      where: { stripeSubscriptionId: subscription.id },
    });

    if (!user) {
      logger.error('User not found for subscription', { subscriptionId: subscription.id });
      return;
    }

    const priceId = subscription.items.data[0]?.price.id;
    const tier = this.getTierFromPriceId(priceId);

    await prisma.user.update({
      where: { id: user.id },
      data: {
        subscriptionTier: tier,
        subscriptionStatus: subscription.status,
      },
    });

    logger.info('Subscription updated', { userId: user.id, tier, status: subscription.status });
  }

  // Handle subscription deleted (cancelled)
  private async handleSubscriptionDeleted(subscription: Stripe.Subscription) {
    const user = await prisma.user.findFirst({
      where: { stripeSubscriptionId: subscription.id },
    });

    if (!user) {
      logger.error('User not found for subscription', { subscriptionId: subscription.id });
      return;
    }

    await prisma.user.update({
      where: { id: user.id },
      data: {
        subscriptionTier: 'FREE',
        subscriptionStatus: 'cancelled',
        stripeSubscriptionId: null,
      },
    });

    logger.info('Subscription cancelled', { userId: user.id });
  }

  // Handle successful payment
  private async handlePaymentSucceeded(invoice: Stripe.Invoice) {
    const customerId = invoice.customer as string;
    const subscriptionId = invoice.subscription as string;

    const user = await prisma.user.findFirst({
      where: { stripeCustomerId: customerId },
    });

    if (!user) {
      logger.error('User not found for payment', { customerId });
      return;
    }

    // Record payment
    await prisma.payment.create({
      data: {
        userId: user.id,
        amount: invoice.amount_paid / 100, // Convert from cents
        currency: invoice.currency.toUpperCase(),
        status: 'COMPLETED',
        stripePaymentId: invoice.payment_intent as string,
        stripeInvoiceId: invoice.id,
        metadata: {
          subscriptionId,
          invoiceNumber: invoice.number,
        },
      },
    });

    logger.info('Payment succeeded', { userId: user.id, amount: invoice.amount_paid / 100 });
  }

  // Handle failed payment
  private async handlePaymentFailed(invoice: Stripe.Invoice) {
    const customerId = invoice.customer as string;

    const user = await prisma.user.findFirst({
      where: { stripeCustomerId: customerId },
    });

    if (!user) {
      logger.error('User not found for failed payment', { customerId });
      return;
    }

    // Record failed payment
    await prisma.payment.create({
      data: {
        userId: user.id,
        amount: invoice.amount_due / 100,
        currency: invoice.currency.toUpperCase(),
        status: 'FAILED',
        stripePaymentId: invoice.payment_intent as string,
        stripeInvoiceId: invoice.id,
        metadata: {
          failureReason: 'Payment failed',
        },
      },
    });

    // Update subscription status
    await prisma.user.update({
      where: { id: user.id },
      data: {
        subscriptionStatus: 'past_due',
      },
    });

    logger.warn('Payment failed', { userId: user.id, amount: invoice.amount_due / 100 });
  }

  // Handle checkout session completed
  private async handleCheckoutCompleted(session: Stripe.Checkout.Session) {
    const customerId = session.customer as string;
    const subscriptionId = session.subscription as string;

    // Get user by email (for new customers)
    const user = await prisma.user.findFirst({
      where: {
        OR: [
          { email: session.customer_details?.email || '' },
          { stripeCustomerId: customerId },
        ],
      },
    });

    if (!user) {
      logger.error('User not found for checkout', { email: session.customer_details?.email });
      return;
    }

    // Update user with Stripe customer ID
    await prisma.user.update({
      where: { id: user.id },
      data: {
        stripeCustomerId: customerId,
        stripeSubscriptionId: subscriptionId,
      },
    });

    logger.info('Checkout completed', { userId: user.id, customerId, subscriptionId });
  }

  // Helper: Get tier from Stripe price ID
  private getTierFromPriceId(priceId: string): 'FREE' | 'BASIC' | 'PREMIUM' | 'ENTERPRISE' {
    // Map price IDs to tiers (these would be configured in environment)
    const tierMap: Record<string, 'FREE' | 'BASIC' | 'PREMIUM' | 'ENTERPRISE'> = {
      [process.env.STRIPE_PRICE_BASIC || '']: 'BASIC',
      [process.env.STRIPE_PRICE_PREMIUM || '']: 'PREMIUM',
      [process.env.STRIPE_PRICE_ENTERPRISE || '']: 'ENTERPRISE',
    };

    return tierMap[priceId] || 'FREE';
  }
}

export const webhookController = new WebhookController();
