import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.get('/', async (req, res) => {
  res.status(501).json({ message: 'List notifications - To be implemented' });
});

router.put('/:id/read', async (req, res) => {
  res.status(501).json({ message: 'Mark notification read - To be implemented' });
});

export default router;
