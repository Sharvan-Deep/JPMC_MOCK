const express = require('express');
const companyController = require('../controllers/companyController');
const asyncHandler = require('../utils/asyncHandler');

const router = express.Router();

router.get('/', asyncHandler(companyController.listCompanies));
router.get('/:companyId/summary', asyncHandler(companyController.getCompanySummary));
router.get('/:companyId', asyncHandler(companyController.getCompanyById));

module.exports = router;
