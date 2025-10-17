import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.post('/chat', async (req, res) => {
  res.status(501).json({ message: 'AI chat - To be implemented' });
});

router.get('/chats', async (req, res) => {
  res.status(501).json({ message: 'List chats - To be implemented' });
});

export default router;
