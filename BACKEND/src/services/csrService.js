const { Company, CSRPolicy, CSRActivity, Source } = require('../models');
const { AppError } = require('../utils/errors');

const COMPANY_CSR_FIELDS =
  'company_name financial_years states csr_sectors wash_record_count latest_financial_year total_wash_spend_crore total_water_spend_crore total_sanitation_spend_crore water_active_years sanitation_active_years wash_focus_evidence source source_retrieved_date';

/**
 * @param {string} companyId
 */
async function getCompanyOrThrow(companyId) {
  const company = await Company.findById(companyId).select(COMPANY_CSR_FIELDS).lean();

  if (!company) {
    throw new AppError('Company not found', 404, { code: 'COMPANY_NOT_FOUND' });
  }

  return company;
}

/**
 * @param {import('mongoose').Document | object} company
 */
function toCompanyIdentification(company) {
  return {
    id: company._id,
    company_name: company.company_name,
  };
}

/**
 * @param {import('mongoose').Document | object} company
 */
function toWashSummary(company) {
  return {
    wash_record_count: company.wash_record_count,
    financial_years: company.financial_years,
    states: company.states,
    csr_sectors: company.csr_sectors,
    latest_financial_year: company.latest_financial_year,
    total_wash_spend_crore: company.total_wash_spend_crore,
    total_water_spend_crore: company.total_water_spend_crore,
    total_sanitation_spend_crore: company.total_sanitation_spend_crore,
    water_active_years: company.water_active_years,
    sanitation_active_years: company.sanitation_active_years,
    wash_focus_evidence: company.wash_focus_evidence,
    source: company.source,
    source_retrieved_date: company.source_retrieved_date,
  };
}

/**
 * @param {import('mongoose').Document | object} policy
 */
function toSafePolicy(policy) {
  const obj = policy.toObject ? policy.toObject() : policy;

  return {
    id: obj._id,
    financialYear: obj.financialYear,
    title: obj.title,
    policyText: obj.policyText,
    policyUrl: obj.policyUrl,
    source: obj.source,
    retrievedAt: obj.retrievedAt,
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

/**
 * @param {import('mongoose').Document | object} policy
 */
function toPolicySummary(policy) {
  const obj = policy.toObject ? policy.toObject() : policy;

  return {
    id: obj._id,
    financialYear: obj.financialYear,
    title: obj.title,
    policyUrl: obj.policyUrl,
    source: obj.source,
    retrievedAt: obj.retrievedAt,
  };
}

/**
 * @param {import('mongoose').Document | object} source
 */
function toSafeActivity(activity) {
  const obj = activity.toObject ? activity.toObject() : activity;

  return {
    id: obj._id,
    financialYear: obj.financialYear,
    psuStatus: obj.psuStatus,
    state: obj.state,
    developmentSector: obj.developmentSector,
    subDevelopmentSector: obj.subDevelopmentSector,
    amountSpentCrore: obj.amountSpentCrore,
    sourceName: obj.sourceName,
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

function toSafeSource(source) {
  const obj = source.toObject ? source.toObject() : source;

  return {
    id: obj._id,
    sourceType: obj.sourceType,
    sourceName: obj.sourceName,
    sourceUrl: obj.sourceUrl,
    retrievedAt: obj.retrievedAt,
    createdAt: obj.createdAt,
  };
}

/**
 * @param {string} companyId
 */
async function getCsrOverview(companyId) {
  const company = await getCompanyOrThrow(companyId);

  const [
    policyCount,
    policyYears,
    sourceCount,
    recentPolicies,
    activityCount,
    activityYears,
    activitySpend,
    recentActivities,
  ] = await Promise.all([
    CSRPolicy.countDocuments({ company: companyId }),
    CSRPolicy.distinct('financialYear', {
      company: companyId,
      financialYear: { $exists: true, $ne: '' },
    }),
    Source.countDocuments({ company: companyId }),
    CSRPolicy.find({ company: companyId })
      .sort({ createdAt: -1 })
      .limit(5)
      .select('financialYear title policyUrl source retrievedAt createdAt')
      .lean(),
    CSRActivity.countDocuments({ company: companyId }),
    CSRActivity.distinct('financialYear', {
      company: companyId,
      financialYear: { $exists: true, $ne: '' },
    }),
    CSRActivity.aggregate([
      { $match: { company: company._id } },
      { $group: { _id: null, totalSpendCrore: { $sum: '$amountSpentCrore' } } },
    ]),
    CSRActivity.find({ company: companyId })
      .sort({ financialYear: -1, createdAt: -1 })
      .limit(10)
      .lean(),
  ]);

  const availableFinancialYears = [
    ...new Set([
      ...(company.financial_years || []),
      ...policyYears.filter(Boolean),
      ...activityYears.filter(Boolean),
    ]),
  ].sort();

  return {
    company: toCompanyIdentification(company),
    policyCount,
    sourceCount,
    availableFinancialYears,
    washSummary: toWashSummary(company),
    recentPolicies: recentPolicies.map(toPolicySummary),
    activities: {
      count: activityCount,
      totalSpendCrore: activitySpend[0]?.totalSpendCrore || 0,
      financialYears: activityYears.filter(Boolean).sort(),
      recent: recentActivities.map(toSafeActivity),
    },
  };
}

/**
 * @param {string} companyId
 * @param {Record<string, unknown>} query
 */
async function listPolicies(companyId, query) {
  await getCompanyOrThrow(companyId);

  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 10));
  const skip = (page - 1) * limit;
  const filter = { company: companyId };

  if (query.financialYear) {
    filter.financialYear = query.financialYear;
  }

  const sortField = ['financialYear', 'title', 'retrievedAt', 'createdAt'].includes(query.sort)
    ? query.sort
    : 'createdAt';
  const sortOrder = String(query.order || 'desc').toLowerCase() === 'asc' ? 1 : -1;

  const [policies, total] = await Promise.all([
    CSRPolicy.find(filter)
      .sort({ [sortField]: sortOrder })
      .skip(skip)
      .limit(limit)
      .lean(),
    CSRPolicy.countDocuments(filter),
  ]);

  return {
    policies: policies.map(toSafePolicy),
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit) || 0,
    },
  };
}

/**
 * @param {string} companyId
 * @param {string} policyId
 */
async function getPolicyById(companyId, policyId) {
  await getCompanyOrThrow(companyId);

  const policy = await CSRPolicy.findOne({
    _id: policyId,
    company: companyId,
  }).lean();

  if (!policy) {
    throw new AppError('CSR policy not found', 404, { code: 'CSR_POLICY_NOT_FOUND' });
  }

  return toSafePolicy(policy);
}

/**
 * @param {string} companyId
 * @param {Record<string, unknown>} query
 */
async function listSources(companyId, query) {
  await getCompanyOrThrow(companyId);

  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 10));
  const skip = (page - 1) * limit;
  const filter = { company: companyId };

  if (query.sourceType) {
    filter.sourceType = query.sourceType;
  }

  const sortField = ['sourceType', 'sourceName', 'retrievedAt', 'createdAt'].includes(query.sort)
    ? query.sort
    : 'createdAt';
  const sortOrder = String(query.order || 'desc').toLowerCase() === 'asc' ? 1 : -1;

  const [sources, total] = await Promise.all([
    Source.find(filter)
      .sort({ [sortField]: sortOrder })
      .skip(skip)
      .limit(limit)
      .lean(),
    Source.countDocuments(filter),
  ]);

  return {
    sources: sources.map(toSafeSource),
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit) || 0,
    },
  };
}

module.exports = {
  getCsrOverview,
  listPolicies,
  getPolicyById,
  listSources,
};
