const mongoose = require('mongoose');

const SORTABLE_POLICY_FIELDS = ['financialYear', 'title', 'retrievedAt', 'createdAt'];
const SORTABLE_SOURCE_FIELDS = ['sourceType', 'sourceName', 'retrievedAt', 'createdAt'];

/**
 * @param {unknown} value
 * @param {string} fieldName
 */
function validateObjectId(value, fieldName) {
  if (!value || typeof value !== 'string' || !mongoose.Types.ObjectId.isValid(value)) {
    return { valid: false, errors: [`Invalid ${fieldName}`] };
  }

  return { valid: true, errors: [], value };
}

/**
 * @param {Record<string, unknown>} query
 */
function validateListPoliciesQuery(query = {}) {
  const errors = [];
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 10));
  const data = { page, limit };

  if (query.financialYear) {
    const financialYear = String(query.financialYear).trim();

    if (!financialYear) {
      errors.push('financialYear cannot be empty');
    } else {
      data.financialYear = financialYear;
    }
  }

  if (query.sort) {
    if (!SORTABLE_POLICY_FIELDS.includes(String(query.sort))) {
      errors.push('Invalid sort field');
    } else {
      data.sort = String(query.sort);
    }
  }

  if (query.order) {
    const order = String(query.order).toLowerCase();

    if (!['asc', 'desc'].includes(order)) {
      errors.push('Invalid sort order');
    } else {
      data.order = order;
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return { valid: true, errors: [], data };
}

/**
 * @param {Record<string, unknown>} query
 */
function validateListSourcesQuery(query = {}) {
  const errors = [];
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 10));
  const data = { page, limit };

  if (query.sourceType) {
    const sourceType = String(query.sourceType).trim();

    if (!sourceType) {
      errors.push('sourceType cannot be empty');
    } else {
      data.sourceType = sourceType;
    }
  }

  if (query.sort) {
    if (!SORTABLE_SOURCE_FIELDS.includes(String(query.sort))) {
      errors.push('Invalid sort field');
    } else {
      data.sort = String(query.sort);
    }
  }

  if (query.order) {
    const order = String(query.order).toLowerCase();

    if (!['asc', 'desc'].includes(order)) {
      errors.push('Invalid sort order');
    } else {
      data.order = order;
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return { valid: true, errors: [], data };
}

module.exports = {
  validateObjectId,
  validateListPoliciesQuery,
  validateListSourcesQuery,
};
