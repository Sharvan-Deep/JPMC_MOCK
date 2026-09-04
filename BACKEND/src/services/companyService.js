const { Company } = require('../models');
const { isValidObjectId } = require('../utils/objectId');

/**
 * Escape special regex characters for safe partial name search.
 */
function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Build MongoDB filter from list query options.
 */
function buildListFilter({ search, latestFinancialYear, state, csrSector }) {
  const filter = {};

  if (search) {
    filter.company_name = { $regex: escapeRegex(search), $options: 'i' };
  }

  if (latestFinancialYear) {
    filter.latest_financial_year = latestFinancialYear;
  }

  if (state) {
    filter.states = state;
  }

  if (csrSector) {
    filter.csr_sectors = csrSector;
  }

  return filter;
}

/**
 * Map a company document to a public API shape (excludes internal fields).
 */
function toPublicCompany(doc) {
  if (!doc) {
    return null;
  }

  const { companyNameKey, __v, ...publicFields } = doc;
  return publicFields;
}

/**
 * Map a company document to a concise summary shape.
 */
function toCompanySummary(doc) {
  return {
    _id: doc._id,
    company_name: doc.company_name,
    wash_record_count: doc.wash_record_count,
    financial_years: doc.financial_years,
    states: doc.states,
    csr_sectors: doc.csr_sectors,
    total_wash_spend_crore: doc.total_wash_spend_crore,
    latest_financial_year: doc.latest_financial_year,
    total_water_spend_crore: doc.total_water_spend_crore,
    total_sanitation_spend_crore: doc.total_sanitation_spend_crore,
    water_active_years: doc.water_active_years,
    sanitation_active_years: doc.sanitation_active_years,
    wash_focus_evidence: doc.wash_focus_evidence,
    source: doc.source,
    source_retrieved_date: doc.source_retrieved_date,
  };
}

/**
 * List companies with pagination, search, filters, and sorting.
 */
async function listCompanies(options) {
  const filter = buildListFilter(options);
  const sortDirection = options.sortOrder === 'asc' ? 1 : -1;
  const skip = (options.page - 1) * options.limit;

  const [companies, total] = await Promise.all([
    Company.find(filter)
      .select('-companyNameKey -__v')
      .sort({ [options.sortBy]: sortDirection })
      .skip(skip)
      .limit(options.limit)
      .lean(),
    Company.countDocuments(filter),
  ]);

  return {
    companies,
    pagination: {
      page: options.page,
      limit: options.limit,
      total,
      totalPages: total > 0 ? Math.ceil(total / options.limit) : 0,
    },
  };
}

/**
 * Fetch a single company by MongoDB ObjectId.
 */
async function getCompanyById(companyId) {
  if (!isValidObjectId(companyId)) {
    const error = new Error('Invalid company ID');
    error.statusCode = 400;
    throw error;
  }

  const company = await Company.findById(companyId).select('-companyNameKey -__v').lean();

  if (!company) {
    const error = new Error('Company not found');
    error.statusCode = 404;
    throw error;
  }

  return toPublicCompany(company);
}

/**
 * Fetch a concise WASH summary for a company.
 */
async function getCompanySummary(companyId) {
  if (!isValidObjectId(companyId)) {
    const error = new Error('Invalid company ID');
    error.statusCode = 400;
    throw error;
  }

  const company = await Company.findById(companyId)
    .select(
      'company_name wash_record_count financial_years states csr_sectors total_wash_spend_crore latest_financial_year total_water_spend_crore total_sanitation_spend_crore water_active_years sanitation_active_years wash_focus_evidence source source_retrieved_date'
    )
    .lean();

  if (!company) {
    const error = new Error('Company not found');
    error.statusCode = 404;
    throw error;
  }

  return toCompanySummary(company);
}

module.exports = {
  listCompanies,
  getCompanyById,
  getCompanySummary,
};
