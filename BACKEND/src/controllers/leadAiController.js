const leadScoringService = require('../services/leadScoringService');
const recommendationService = require('../services/recommendationService');
const outreachService = require('../services/outreachService');
const { AppError } = require('../utils/errors');
const {
  validateRecommendBody,
  validateOutreachGenerateBody,
  validateScoreBatchBody,
  validatePaginationQuery,
} = require('../validators/aiIntegrationValidator');

async function scoreLead(req, res) {
  const data = await leadScoringService.scoreLead(req.params.leadId, req.user);

  res.json({
    success: true,
    data,
  });
}

async function scoreLeadsBatch(req, res) {
  const validation = validateScoreBatchBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await leadScoringService.scoreLeadsBatch(validation.data.leadIds, req.user);

  res.json({
    success: true,
    data,
  });
}

async function listTopLeads(req, res) {
  const query = validatePaginationQuery(req.query);
  const data = await leadScoringService.listTopLeads(query.data, req.user);

  res.json({
    success: true,
    data,
  });
}

async function recommendLead(req, res) {
  const validation = validateRecommendBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await recommendationService.recommendForLead(
    req.params.leadId,
    req.user,
    validation.data
  );

  res.json({
    success: true,
    data,
  });
}

async function generateOutreach(req, res) {
  const validation = validateOutreachGenerateBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await outreachService.generateOutreach(
    req.params.leadId,
    req.user,
    validation.data
  );

  res.status(201).json({
    success: true,
    data,
  });
}

module.exports = {
  scoreLead,
  scoreLeadsBatch,
  listTopLeads,
  recommendLead,
  generateOutreach,
};
