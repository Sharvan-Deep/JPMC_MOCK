const express = require('express');
const userController = require('../controllers/userController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const { requireAdmin, validateObjectIdParam } = require('../middleware/requireAdmin');

const router = express.Router();

router.use(requireAuth);
router.use(requireAdmin);

router.get('/', asyncHandler(userController.listUsers));

router.get(
  '/:userId',
  validateObjectIdParam('userId'),
  asyncHandler(userController.getUser)
);

router.patch(
  '/:userId',
  validateObjectIdParam('userId'),
  asyncHandler(userController.updateUser)
);

router.patch(
  '/:userId/role',
  validateObjectIdParam('userId'),
  asyncHandler(userController.updateRole)
);

router.patch(
  '/:userId/status',
  validateObjectIdParam('userId'),
  asyncHandler(userController.updateStatus)
);

module.exports = router;
