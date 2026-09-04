/**
 * @param {Record<string, unknown>} query
 * @param {{ defaultLimit?: number }} [options]
 */
function validatePaginationQuery(query = {}, options = {}) {
  const errors = [];
  const defaultLimit = options.defaultLimit ?? 10;
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || defaultLimit));

  if (query.page !== undefined && query.page !== null && query.page !== '') {
    const parsedPage = Number(query.page);

    if (!Number.isInteger(parsedPage) || parsedPage < 1) {
      errors.push('page must be a positive integer');
    }
  }

  if (query.limit !== undefined && query.limit !== null && query.limit !== '') {
    const parsedLimit = Number(query.limit);

    if (!Number.isInteger(parsedLimit) || parsedLimit < 1) {
      errors.push('limit must be a positive integer');
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: { page, limit },
  };
}

module.exports = {
  validatePaginationQuery,
};
