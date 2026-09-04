const express = require('express');
const companyController = require('../controllers/companyController');
const companyAiController = require('../controllers/companyAiController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { validateObjectIdParam } = require('../middleware/requireAdmin');
const { USER_ROLES } = require('../config/constants');

const router = express.Router();

router.use(requireAuth);
router.use(requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF));

router.get('/', asyncHandler(companyController.listCompanies));
router.post('/discover', asyncHandler(companyAiController.discoverCompanies));

router.post(
  '/:companyId/analyze',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.analyzeCompany)
);
router.post(
  '/:companyId/verify',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.verifyCompany)
);
router.get(
  '/:companyId/freshness/history',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.getFreshnessHistory)
);
router.get(
  '/:companyId/freshness',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.getFreshness)
);
router.get(
  '/:companyId/recommendations',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.getRecommendations)
);
router.post(
  '/:companyId/copilot/chat',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.copilotChat)
);
router.get(
  '/:companyId/outreach/audit',
  validateObjectIdParam('companyId'),
  asyncHandler(companyAiController.getOutreachAudit)
);

router.get(
  '/:companyId/summary',
  validateObjectIdParam('companyId'),
  asyncHandler(companyController.getCompanySummary)
);
router.get(
  '/:companyId',
  validateObjectIdParam('companyId'),
  asyncHandler(companyController.getCompanyById)
);

module.exports = router;
