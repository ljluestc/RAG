import Stripe from 'stripe';
import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';

export class PaymentService {
  private stripe: Stripe | null = null;

  constructor() {
    if (process.env.STRIPE_SECRET_KEY) {
      this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
        apiVersion: '2024-12-18.acacia',
      });
    }
  }

  async createCheckoutSession(
    userId: string,
    priceId: string,
    successUrl: string,
    cancelUrl: string
  ) {
    if (!this.stripe) {
      throw new AppError('Stripe not configured', 500);
    }

    try {
      const user = await prisma.user.findUnique({
        where: { id: userId },
        select: { email: true, customerId: true },
      });

      if (!user) {
        throw new AppError('User not found', 404);
      }

      // Create or get Stripe customer
      let customerId = user.customerId;
      if (!customerId) {
        const customer = await this.stripe.customers.create({
          email: user.email,
          metadata: { userId },
        });
        customerId = customer.id;

        await prisma.user.update({
          where: { id: userId },
          data: { customerId },
        });
      }

      // Create checkout session
      const session = await this.stripe.checkout.sessions.create({
        customer: customerId,
        payment_method_types: ['card'],
        line_items: [{ price: priceId, quantity: 1 }],
        mode: 'subscription',
        success_url: successUrl,
        cancel_url: cancelUrl,
        metadata: { userId },
      });

      logger.info('Checkout session created', { userId, sessionId: session.id });

      return { sessionId: session.id, url: session.url };
    } catch (error) {
      logger.error('Create checkout session error', { error, userId });
      throw error;
    }
  }

  async handleWebhook(event: any) {
    try {
      switch (event.type) {
        case 'checkout.session.completed':
          await this.handleCheckoutComplete(event.data.object);
          break;
        case 'customer.subscription.updated':
          await this.handleSubscriptionUpdate(event.data.object);
          break;
        case 'customer.subscription.deleted':
          await this.handleSubscriptionCancel(event.data.object);
          break;
        default:
          logger.info('Unhandled webhook event', { type: event.type });
      }
    } catch (error) {
      logger.error('Webhook handling error', { error, eventType: event.type });
      throw error;
    }
  }

  private async handleCheckoutComplete(session: any) {
    const userId = session.metadata.userId;

    await prisma.subscription.upsert({
      where: { userId },
      update: {
        stripeSubscriptionId: session.subscription,
        stripeCustomerId: session.customer,
        status: 'ACTIVE',
        tier: 'PRO',
      },
      create: {
        userId,
        stripeSubscriptionId: session.subscription,
        stripeCustomerId: session.customer,
        status: 'ACTIVE',
        tier: 'PRO',
      },
    });

    await prisma.user.update({
      where: { id: userId },
      data: { subscriptionTier: 'PRO' },
    });

    logger.info('Subscription activated', { userId });
  }

  private async handleSubscriptionUpdate(subscription: any) {
    const customerId = subscription.customer;

    const user = await prisma.user.findFirst({
      where: { customerId },
    });

    if (!user) return;

    await prisma.subscription.update({
      where: { userId: user.id },
      data: {
        status: subscription.status.toUpperCase(),
        stripeCurrentPeriodEnd: new Date(subscription.current_period_end * 1000),
      },
    });

    logger.info('Subscription updated', { userId: user.id });
  }

  private async handleSubscriptionCancel(subscription: any) {
    const customerId = subscription.customer;

    const user = await prisma.user.findFirst({
      where: { customerId },
    });

    if (!user) return;

    await prisma.subscription.update({
      where: { userId: user.id },
      data: {
        status: 'CANCELED',
        canceledAt: new Date(),
      },
    });

    await prisma.user.update({
      where: { id: user.id },
      data: { subscriptionTier: 'FREE' },
    });

    logger.info('Subscription canceled', { userId: user.id });
  }

  async getSubscriptionStatus(userId: string) {
    try {
      const subscription = await prisma.subscription.findUnique({
        where: { userId },
      });

      return subscription;
    } catch (error) {
      logger.error('Get subscription status error', { error, userId });
      throw error;
    }
  }

  async cancelSubscription(userId: string) {
    if (!this.stripe) {
      throw new AppError('Stripe not configured', 500);
    }

    try {
      const subscription = await prisma.subscription.findUnique({
        where: { userId },
      });

      if (!subscription?.stripeSubscriptionId) {
        throw new AppError('No active subscription found', 404);
      }

      await this.stripe.subscriptions.update(subscription.stripeSubscriptionId, {
        cancel_at_period_end: true,
      });

      await prisma.subscription.update({
        where: { userId },
        data: { cancelAtPeriodEnd: true },
      });

      logger.info('Subscription cancellation scheduled', { userId });

      return { message: 'Subscription will cancel at period end' };
    } catch (error) {
      logger.error('Cancel subscription error', { error, userId });
      throw error;
    }
  }
}

export const paymentService = new PaymentService();
