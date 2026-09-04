const csrService = require('../services/csrService');
const { AppError } = require('../utils/errors');
const {
  validateListPoliciesQuery,
  validateListSourcesQuery,
} = require('../validators/csrValidator');

async function getCsrOverview(req, res) {
  const data = await csrService.getCsrOverview(req.params.companyId);

  res.json({
    success: true,
    data,
  });
}

async function listPolicies(req, res) {
  const validation = validateListPoliciesQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await csrService.listPolicies(req.params.companyId, validation.data);

  res.json({
    success: true,
    data,
  });
}

async function getPolicy(req, res) {
  const policy = await csrService.getPolicyById(
    req.params.companyId,
    req.params.policyId
  );

  res.json({
    success: true,
    data: { policy },
  });
}

async function listSources(req, res) {
  const validation = validateListSourcesQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await csrService.listSources(req.params.companyId, validation.data);

  res.json({
    success: true,
    data,
  });
}

module.exports = {
  getCsrOverview,
  listPolicies,
  getPolicy,
  listSources,
};
