const companyAiService = require('../services/companyAiService');
const outreachService = require('../services/outreachService');
const aiService = require('../services/aiService');
const { AppError } = require('../utils/errors');
const {
  validateDiscoverBody,
  validateCopilotChatBody,
  validatePaginationQuery,
} = require('../validators/aiIntegrationValidator');

async function getAiHealth(_req, res) {
  const health = await aiService.health();

  res.json({
    success: true,
    data: { health },
  });
}

async function discoverCompanies(req, res) {
  const validation = validateDiscoverBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await companyAiService.discoverCompanies(validation.data);

  res.json({
    success: true,
    data,
  });
}

async function analyzeCompany(req, res) {
  const data = await companyAiService.analyzeCompany(req.params.companyId);

  res.json({
    success: true,
    data,
  });
}

async function verifyCompany(req, res) {
  const data = await companyAiService.verifyCompany(req.params.companyId);

  res.json({
    success: true,
    data,
  });
}

async function getFreshness(req, res) {
  const data = await companyAiService.getCompanyFreshness(req.params.companyId);

  res.json({
    success: true,
    data,
  });
}

async function getFreshnessHistory(req, res) {
  const query = validatePaginationQuery(req.query);
  const data = await companyAiService.getCompanyFreshnessHistory(req.params.companyId, query.data);

  res.json({
    success: true,
    data,
  });
}

async function getRecommendations(req, res) {
  const query = validatePaginationQuery(req.query);
  const data = await companyAiService.getCompanyRecommendations(req.params.companyId, query.data);

  res.json({
    success: true,
    data,
  });
}

async function copilotChat(req, res) {
  const validation = validateCopilotChatBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await companyAiService.chatWithCopilot(req.params.companyId, validation.data);

  res.json({
    success: true,
    data,
  });
}

async function getOutreachAudit(req, res) {
  const query = validatePaginationQuery(req.query);
  const data = await outreachService.getCompanyOutreachAudit(
    req.params.companyId,
    req.user,
    query.data
  );

  res.json({
    success: true,
    data,
  });
}

module.exports = {
  getAiHealth,
  discoverCompanies,
  analyzeCompany,
  verifyCompany,
  getFreshness,
  getFreshnessHistory,
  getRecommendations,
  copilotChat,
  getOutreachAudit,
};
