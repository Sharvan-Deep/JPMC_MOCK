const dashboardService = require('../services/dashboardService');
const { AppError } = require('../utils/errors');
const { validatePaginationQuery } = require('../validators/dashboardValidator');

async function getSummary(_req, res) {
  const data = await dashboardService.getDashboardSummary();

  res.json({
    success: true,
    data,
  });
}

async function getTopProspects(req, res) {
  const validation = validatePaginationQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await dashboardService.getTopProspects(validation.data);

  res.json({
    success: true,
    data,
  });
}

async function getRecentLeads(req, res) {
  const validation = validatePaginationQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await dashboardService.getRecentLeads(validation.data);

  res.json({
    success: true,
    data,
  });
}

async function getFollowUps(req, res) {
  const validation = validatePaginationQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await dashboardService.getFollowUps(validation.data);

  res.json({
    success: true,
    data,
  });
}

module.exports = {
  getSummary,
  getTopProspects,
  getRecentLeads,
  getFollowUps,
};
