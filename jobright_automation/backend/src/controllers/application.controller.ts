import { Router } from 'express';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();
router.use(authenticate);

router.get('/', async (req, res) => {
  res.status(501).json({ message: 'List applications - To be implemented' });
});

router.post('/', async (req, res) => {
  res.status(501).json({ message: 'Create application - To be implemented' });
});

router.get('/:id', async (req, res) => {
  res.status(501).json({ message: 'Get application - To be implemented' });
});

router.put('/:id/status', async (req, res) => {
  res.status(501).json({ message: 'Update application status - To be implemented' });
});

export default router;
