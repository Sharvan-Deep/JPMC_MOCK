const DEFAULT_PAGE = 1;
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;
const DEFAULT_SORT_ORDER = 'desc';

const ALLOWED_SORT_FIELDS = [
  'company_name',
  'wash_record_count',
  'latest_financial_year',
  'total_wash_spend_crore',
  'total_water_spend_crore',
  'total_sanitation_spend_crore',
  'createdAt',
  'updatedAt',
];

/**
 * Parse and validate list query parameters for GET /api/companies.
 *
 * @param {import('express').Request['query']} query
 * @returns {{ page: number, limit: number, search: string, latestFinancialYear: string, state: string, csrSector: string, sortBy: string, sortOrder: 'asc' | 'desc' }}
 */
function parseCompanyListQuery(query) {
  const page = Math.max(DEFAULT_PAGE, parseInt(query.page, 10) || DEFAULT_PAGE);
  const rawLimit = parseInt(query.limit, 10) || DEFAULT_LIMIT;
  const limit = Math.min(Math.max(1, rawLimit), MAX_LIMIT);

  const sortBy = query.sortBy ? String(query.sortBy).trim() : 'company_name';
  if (!ALLOWED_SORT_FIELDS.includes(sortBy)) {
    const error = new Error(`Invalid sortBy. Allowed values: ${ALLOWED_SORT_FIELDS.join(', ')}`);
    error.statusCode = 400;
    throw error;
  }

  const sortOrderRaw = query.sortOrder ? String(query.sortOrder).trim().toLowerCase() : DEFAULT_SORT_ORDER;
  if (sortOrderRaw !== 'asc' && sortOrderRaw !== 'desc') {
    const error = new Error('Invalid sortOrder. Allowed values: asc, desc');
    error.statusCode = 400;
    throw error;
  }

  return {
    page,
    limit,
    search: query.search ? String(query.search).trim() : '',
    latestFinancialYear: query.latestFinancialYear ? String(query.latestFinancialYear).trim() : '',
    state: query.state ? String(query.state).trim() : '',
    csrSector: query.csrSector ? String(query.csrSector).trim() : '',
    sortBy,
    sortOrder: sortOrderRaw,
  };
}

module.exports = {
  parseCompanyListQuery,
  ALLOWED_SORT_FIELDS,
};
