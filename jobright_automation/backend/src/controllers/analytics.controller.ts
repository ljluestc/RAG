import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.get('/dashboard', async (req, res) => {
  res.status(501).json({ message: 'Analytics dashboard - To be implemented' });
});

export default router;
