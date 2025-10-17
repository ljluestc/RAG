import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.get('/', async (req, res) => {
  res.status(501).json({ message: 'List resumes - To be implemented' });
});

router.post('/', async (req, res) => {
  res.status(501).json({ message: 'Create resume - To be implemented' });
});

router.post('/generate', async (req, res) => {
  res.status(501).json({ message: 'AI generate resume - To be implemented' });
});

router.post('/:id/optimize', async (req, res) => {
  res.status(501).json({ message: 'Optimize resume - To be implemented' });
});

export default router;
