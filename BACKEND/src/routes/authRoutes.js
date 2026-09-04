const multer = require('multer');
const express = require('express');
const authController = require('../controllers/authController');
const invitationController = require('../controllers/invitationController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const {
  requireAdmin,
  validateObjectIdParam,
} = require('../middleware/requireAdmin');

const router = express.Router();

const csvUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const isCsvMime =
      file.mimetype === 'text/csv' ||
      file.mimetype === 'application/vnd.ms-excel' ||
      file.mimetype === 'text/plain';
    const isCsvName = file.originalname.toLowerCase().endsWith('.csv');

    if (isCsvMime || isCsvName) {
      cb(null, true);
    } else {
      cb(new Error('Only CSV files are allowed'));
    }
  },
});

router.post('/login', asyncHandler(authController.login));
router.post('/refresh', asyncHandler(authController.refresh));
router.post('/logout', asyncHandler(authController.logout));
router.get('/me', requireAuth, asyncHandler(authController.me));

router.post(
  '/invitations',
  requireAuth,
  requireAdmin,
  asyncHandler(invitationController.createInvitation)
);

router.get(
  '/invitations',
  requireAuth,
  requireAdmin,
  asyncHandler(invitationController.listInvitations)
);

router.post(
  '/invitations/verify',
  asyncHandler(invitationController.verifyInvitation)
);

router.post(
  '/invitations/import',
  requireAuth,
  requireAdmin,
  csvUpload.single('file'),
  asyncHandler(invitationController.importInvitations)
);

router.get(
  '/invitations/:invitationId',
  requireAuth,
  requireAdmin,
  validateObjectIdParam('invitationId'),
  asyncHandler(invitationController.getInvitation)
);

router.post(
  '/invitations/:invitationId/resend',
  requireAuth,
  requireAdmin,
  validateObjectIdParam('invitationId'),
  asyncHandler(invitationController.resendInvitation)
);

router.delete(
  '/invitations/:invitationId',
  requireAuth,
  requireAdmin,
  validateObjectIdParam('invitationId'),
  asyncHandler(invitationController.revokeInvitation)
);

router.post('/activate', asyncHandler(invitationController.activateAccount));

module.exports = router;
