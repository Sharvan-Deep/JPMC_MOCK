const { CSR_ACTIVITY_CSV_HEADERS } = require('../config/constants');

/**
 * Validate that a CSR activity CSV contains the required columns.
 * Matching is case-insensitive; extra columns are ignored.
 *
 * @param {string[]} headers
 */
function validateCsrActivityCsvHeaders(headers) {
  const normalizedHeaders = headers.map((h) => String(h).trim().toLowerCase());
  const expected = CSR_ACTIVITY_CSV_HEADERS.map((h) => h.toLowerCase());

  const missing = expected.filter((col) => !normalizedHeaders.includes(col));
  const extra = normalizedHeaders.filter((col) => !expected.includes(col) && col !== '');

  return {
    valid: missing.length === 0,
    missing,
    extra,
  };
}

/**
 * @param {object} doc
 */
function validateCsrActivityDocument(doc) {
  const errors = [];

  if (!doc.companyName || !String(doc.companyName).trim()) {
    errors.push('Company Name is required');
  }

  if (doc.amountSpentCrore !== undefined && doc.amountSpentCrore < 0) {
    errors.push('Project Amount Spent must be non-negative');
  }

  if (
    doc.amountSpentCrore !== undefined &&
    typeof doc.amountSpentCrore === 'number' &&
    !Number.isFinite(doc.amountSpentCrore)
  ) {
    errors.push('Project Amount Spent must be a finite number');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

module.exports = {
  validateCsrActivityCsvHeaders,
  validateCsrActivityDocument,
};
