const express = require('express');
const dashboardController = require('../controllers/dashboardController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { USER_ROLES } = require('../config/constants');

const router = express.Router();

router.use(requireAuth);
router.use(requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF));

router.get('/summary', asyncHandler(dashboardController.getSummary));
router.get('/top-prospects', asyncHandler(dashboardController.getTopProspects));
router.get('/recent-leads', asyncHandler(dashboardController.getRecentLeads));
router.get('/follow-ups', asyncHandler(dashboardController.getFollowUps));

module.exports = router;
