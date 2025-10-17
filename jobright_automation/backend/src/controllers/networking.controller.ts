import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.get('/connections', async (req, res) => {
  res.status(501).json({ message: 'List connections - To be implemented' });
});

router.get('/discover', async (req, res) => {
  res.status(501).json({ message: 'Discover connections - To be implemented' });
});

export default router;
