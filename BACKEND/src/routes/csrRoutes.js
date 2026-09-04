const express = require('express');
const csrController = require('../controllers/csrController');
const asyncHandler = require('../utils/asyncHandler');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { validateObjectIdParam } = require('../middleware/requireAdmin');
const { USER_ROLES } = require('../config/constants');

const router = express.Router({ mergeParams: true });

router.use(requireAuth);
router.use(requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF));
router.use(validateObjectIdParam('companyId'));

router.get('/csr', asyncHandler(csrController.getCsrOverview));

router.get('/csr/policies', asyncHandler(csrController.listPolicies));

router.get(
  '/csr/policies/:policyId',
  validateObjectIdParam('policyId'),
  asyncHandler(csrController.getPolicy)
);

router.get('/sources', asyncHandler(csrController.listSources));

module.exports = router;
