const {
  Company,
  CompanyFreshnessHistory,
  CompanyLeadScore,
  CompanyRecommendation,
} = require('../models');
const aiService = require('./aiService');
const {
  loadCompanyAiContext,
  buildCanonicalCompanyPayload,
  buildDocumentText,
  buildCandidateScoringInput,
} = require('./aiContextService');
const { extractEvidence, asStringArray, firstDefined } = require('../utils/aiEvidence');
const { AppError } = require('../utils/errors');
const { buildCompanyNameKey } = require('../utils/dataNormalization');

function toFreshnessSnapshot(assessment, extras = {}) {
  const verifiedAt = firstDefined(
    assessment?.verified_at,
    assessment?.verifiedAt,
    extras.verified_at,
    new Date()
  );

  return {
    status: firstDefined(assessment?.status, extras.status),
    verification_cycle: firstDefined(
      assessment?.verification_cycle,
      assessment?.verificationCycle,
      extras.verification_cycle
    ),
    verified_at: verifiedAt,
    evidence: extractEvidence(assessment).concat(extractEvidence(extras)),
    assessment,
    warnings: firstDefined(assessment?.warnings, extras.warnings),
  };
}

function toLeadScoreSnapshot(score) {
  return {
    total_score: firstDefined(score?.total_score, score?.totalScore),
    priority_band: firstDefined(score?.priority_band, score?.priorityBand),
    components: score?.components,
    scoring_version: firstDefined(score?.scoring_version, score?.scoringVersion),
    scored_at: firstDefined(score?.scored_at, score?.scoredAt, new Date()),
    positive_factors: asStringArray(score?.positive_factors || score?.positiveFactors),
    limiting_factors: asStringArray(score?.limiting_factors || score?.limitingFactors),
    missing_information: asStringArray(score?.missing_information || score?.missingInformation),
    evidence_coverage: firstDefined(score?.evidence_coverage, score?.evidenceCoverage),
    evidence: extractEvidence(score),
  };
}

function toRecommendationSnapshot(recommendation, companyName) {
  return {
    recommendation_id: firstDefined(
      recommendation?.recommendation_id,
      recommendation?.recommendationId,
      recommendation?.id
    ),
    company: firstDefined(recommendation?.company, companyName),
    recommended_action: firstDefined(
      recommendation?.recommended_action,
      recommendation?.recommendedAction
    ),
    priority_level: firstDefined(recommendation?.priority_level, recommendation?.priorityLevel),
    confidence: recommendation?.confidence,
    reasons: recommendation?.reasons,
    positive_factors: asStringArray(recommendation?.positive_factors || recommendation?.positiveFactors),
    limiting_factors: asStringArray(recommendation?.limiting_factors || recommendation?.limitingFactors),
    missing_information: asStringArray(
      recommendation?.missing_information || recommendation?.missingInformation
    ),
    evidence_sources: extractEvidence(recommendation),
    human_approval_required: recommendation?.human_approval_required !== false,
    advisory_notice: firstDefined(recommendation?.advisory_notice, recommendation?.advisoryNotice, ''),
    generated_at: firstDefined(recommendation?.generated_at, recommendation?.generatedAt, new Date()),
  };
}

async function persistLeadScore(company, scorePayload) {
  const snapshot = toLeadScoreSnapshot(scorePayload);

  await CompanyLeadScore.create({
    companyId: company._id,
    ...snapshot,
    raw: scorePayload,
  });

  await Company.updateOne({ _id: company._id }, { $set: { leadScore: snapshot } });

  return snapshot;
}

async function persistRecommendation(company, recommendationPayload) {
  const snapshot = toRecommendationSnapshot(recommendationPayload, company.company_name);

  await CompanyRecommendation.create({
    companyId: company._id,
    ...snapshot,
    raw: recommendationPayload,
  });

  await Company.updateOne({ _id: company._id }, { $set: { latestRecommendation: snapshot } });

  return snapshot;
}

async function analyzeCompany(companyId) {
  const context = await loadCompanyAiContext(companyId);
  const canonical = buildCanonicalCompanyPayload(context);
  const text = buildDocumentText(canonical);

  const documentBody = {
    company_id: canonical.company_id,
    company: canonical.company,
    document_type: 'csr_company_summary',
    text,
    ...canonical,
  };

  const validation = await aiService.validateDocument(documentBody);
  const classification = await aiService.classifyDocument(documentBody);
  const search = await aiService.searchDocuments({
    company_id: canonical.company_id,
    company: canonical.company,
    query: canonical.company,
  });

  const aiReadySummary = {
    analyzed_at: new Date(),
    validation,
    classification,
    search,
    warnings: []
      .concat(validation?.warnings || [])
      .concat(classification?.warnings || [])
      .concat(search?.warnings || []),
    evidence: [
      ...extractEvidence(validation),
      ...extractEvidence(classification),
      ...extractEvidence(search),
    ],
  };

  await Company.updateOne({ _id: context.company._id }, { $set: { aiReadySummary } });

  return {
    companyId: canonical.company_id,
    company: canonical.company,
    aiReadySummary,
  };
}

async function verifyCompany(companyId) {
  const context = await loadCompanyAiContext(companyId);
  const canonical = buildCanonicalCompanyPayload(context);

  const verifyPayload = {
    company_id: canonical.company_id,
    company: canonical.company,
    current: canonical,
    previous: canonical.freshness,
    missing_evidence_does_not_imply_wash_loss: true,
  };

  const changeVerification = await aiService.verifyChanges(verifyPayload);
  const freshnessAssessment = await aiService.calculateFreshness({
    company_id: canonical.company_id,
    company: canonical.company,
    ...canonical,
    change_verification: changeVerification,
    missing_evidence_does_not_imply_wash_loss: true,
  });

  const snapshot = toFreshnessSnapshot(freshnessAssessment, {
    warnings: changeVerification?.warnings,
    changeVerification,
  });
  snapshot.changeVerification = changeVerification;

  await CompanyFreshnessHistory.create({
    companyId: context.company._id,
    company: canonical.company,
    status: snapshot.status,
    verification_cycle: snapshot.verification_cycle,
    verified_at: snapshot.verified_at,
    evidence: snapshot.evidence,
    assessment: freshnessAssessment,
    changeVerification,
  });

  await Company.updateOne({ _id: context.company._id }, { $set: { freshness: snapshot } });

  return {
    companyId: canonical.company_id,
    company: canonical.company,
    freshness: snapshot,
    changeVerification,
    warnings: snapshot.warnings || changeVerification?.warnings || [],
  };
}

async function getCompanyFreshness(companyId) {
  const context = await loadCompanyAiContext(companyId);

  return {
    companyId: context.company._id.toString(),
    company: context.company.company_name,
    freshness: context.company.freshness || null,
  };
}

async function getCompanyFreshnessHistory(companyId, query = {}) {
  const context = await loadCompanyAiContext(companyId);
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const skip = (page - 1) * limit;

  const filter = { companyId: context.company._id };
  const [items, total] = await Promise.all([
    CompanyFreshnessHistory.find(filter).sort({ verified_at: -1 }).skip(skip).limit(limit).lean(),
    CompanyFreshnessHistory.countDocuments(filter),
  ]);

  return {
    companyId: context.company._id.toString(),
    history: items,
    pagination: {
      page,
      limit,
      total,
      totalPages: total > 0 ? Math.ceil(total / limit) : 0,
    },
  };
}

async function getCompanyRecommendations(companyId, query = {}) {
  const context = await loadCompanyAiContext(companyId);
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const skip = (page - 1) * limit;

  const filter = { companyId: context.company._id };
  const [items, total] = await Promise.all([
    CompanyRecommendation.find(filter).sort({ generated_at: -1 }).skip(skip).limit(limit).lean(),
    CompanyRecommendation.countDocuments(filter),
  ]);

  return {
    companyId: context.company._id.toString(),
    latestRecommendation: context.company.latestRecommendation || null,
    recommendations: items,
    pagination: {
      page,
      limit,
      total,
      totalPages: total > 0 ? Math.ceil(total / limit) : 0,
    },
  };
}

/**
 * Discovery is a boundary over indexed AI search + existing Mongo companies.
 * It does not crawl the web, import CSVs, or create companies.
 */
async function discoverCompanies(body = {}) {
  const query = String(body.query || body.search || '').trim();
  const limit = Math.min(50, Math.max(1, Number(body.limit) || 10));

  if (!query) {
    throw new AppError('query is required', 400, { errors: ['query is required'] });
  }

  const search = await aiService.searchDocuments({
    query,
    limit,
  });

  const hits = Array.isArray(search)
    ? search
    : search?.results || search?.hits || search?.documents || search?.candidates || [];

  const matched = [];

  for (const hit of hits.slice(0, limit)) {
    const name = firstDefined(hit.company, hit.company_name, hit.name);
    if (!name) {
      matched.push({ hit, company: null });
      continue;
    }

    const company = await Company.findOne({ companyNameKey: buildCompanyNameKey(name) })
      .select('-companyNameKey -__v -aiReadySummary')
      .lean();

    matched.push({ hit, company });
  }

  return {
    query,
    limitation:
      'Discovery searches the AI document index and matches existing MongoDB companies by name. It does not crawl, import, or create companies.',
    results: matched,
    warnings: search?.warnings || [],
  };
}

async function chatWithCopilot(companyId, body) {
  const context = await loadCompanyAiContext(companyId);
  const canonical = buildCanonicalCompanyPayload(context);

  const response = await aiService.copilotChat({
    company_id: canonical.company_id,
    company: canonical.company,
    message: body.message,
    ...canonical,
  });

  return {
    companyId: canonical.company_id,
    company: canonical.company,
    response,
    warnings: response?.warnings || [],
  };
}

module.exports = {
  analyzeCompany,
  verifyCompany,
  getCompanyFreshness,
  getCompanyFreshnessHistory,
  getCompanyRecommendations,
  discoverCompanies,
  chatWithCopilot,
  persistLeadScore,
  persistRecommendation,
  toLeadScoreSnapshot,
  toRecommendationSnapshot,
  toFreshnessSnapshot,
  buildCandidateScoringInput,
};
