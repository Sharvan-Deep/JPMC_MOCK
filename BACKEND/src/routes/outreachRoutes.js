const express = require('express');
const outreachController = require('../controllers/outreachController');
const companyAiController = require('../controllers/companyAiController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { USER_ROLES } = require('../config/constants');

const router = express.Router();

router.use(requireAuth);
router.use(requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF));

router.post('/:id/edit', asyncHandler(outreachController.editDraft));
router.get('/:id', asyncHandler(outreachController.getDraft));
router.post('/:id/validate', asyncHandler(outreachController.validateDraft));
router.post('/:id/approve', asyncHandler(outreachController.approveDraft));
router.post('/:id/send', asyncHandler(outreachController.sendDraft));

module.exports = {
  outreachRouter: router,
  aiHealthHandler: asyncHandler(companyAiController.getAiHealth),
};
