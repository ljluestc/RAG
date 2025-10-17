import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.get('/plans', async (req, res) => {
  res.status(501).json({ message: 'List subscription plans - To be implemented' });
});

router.post('/checkout', async (req, res) => {
  res.status(501).json({ message: 'Create checkout session - To be implemented' });
});

router.post('/webhook', async (req, res) => {
  res.status(501).json({ message: 'Stripe webhook - To be implemented' });
});

export default router;
