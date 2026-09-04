const express = require('express');
const leadController = require('../controllers/leadController');
const leadAiController = require('../controllers/leadAiController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { validateObjectIdParam } = require('../middleware/requireAdmin');
const { USER_ROLES } = require('../config/constants');

const router = express.Router();

router.use(requireAuth);
router.use(requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF));

router.post('/', asyncHandler(leadController.createLead));
router.get('/', asyncHandler(leadController.listLeads));
router.get('/top', asyncHandler(leadAiController.listTopLeads));
router.post('/score-batch', asyncHandler(leadAiController.scoreLeadsBatch));

router.get(
  '/:leadId',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.getLead)
);

router.patch(
  '/:leadId',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.updateLead)
);

router.patch(
  '/:leadId/assign',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.assignLead)
);

router.delete(
  '/:leadId',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.archiveLead)
);

router.post(
  '/:leadId/notes',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.addNote)
);

router.get(
  '/:leadId/notes',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.listNotes)
);

router.post(
  '/:leadId/activities',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.addActivity)
);

router.get(
  '/:leadId/activities',
  validateObjectIdParam('leadId'),
  asyncHandler(leadController.listActivities)
);

router.post(
  '/:leadId/score',
  validateObjectIdParam('leadId'),
  asyncHandler(leadAiController.scoreLead)
);
router.post(
  '/:leadId/recommend',
  validateObjectIdParam('leadId'),
  asyncHandler(leadAiController.recommendLead)
);
router.post(
  '/:leadId/outreach/generate',
  validateObjectIdParam('leadId'),
  asyncHandler(leadAiController.generateOutreach)
);

module.exports = router;
