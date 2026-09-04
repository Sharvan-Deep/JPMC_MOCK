const { COMPANY_CSV_HEADERS } = require('../config/constants');

/**
 * Validate that a CSV header row contains all required columns.
 * Column order does not matter; extra columns are ignored.
 *
 * @param {string[]} headers - Parsed header row from CSV
 * @returns {{ valid: boolean, missing: string[], extra: string[] }}
 */
function validateCompanyCsvHeaders(headers) {
  const normalizedHeaders = headers.map((h) => String(h).trim().toLowerCase());
  const expected = COMPANY_CSV_HEADERS.map((h) => h.toLowerCase());

  const missing = expected.filter((col) => !normalizedHeaders.includes(col));
  const extra = normalizedHeaders.filter((col) => !expected.includes(col) && col !== '');

  return {
    valid: missing.length === 0,
    missing,
    extra,
  };
}

/**
 * Basic validation for a normalized company document before upsert.
 *
 * @param {object} doc - Normalized company fields
 * @returns {{ valid: boolean, errors: string[] }}
 */
function validateCompanyDocument(doc) {
  const errors = [];

  if (!doc.company_name || !String(doc.company_name).trim()) {
    errors.push('company_name is required');
  }

  if (doc.wash_record_count !== undefined && doc.wash_record_count < 0) {
    errors.push('wash_record_count must be non-negative');
  }

  const numericFields = [
    'total_wash_spend_crore',
    'total_water_spend_crore',
    'total_sanitation_spend_crore',
  ];

  for (const field of numericFields) {
    if (doc[field] !== undefined && doc[field] < 0) {
      errors.push(`${field} must be non-negative`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

module.exports = {
  validateCompanyCsvHeaders,
  validateCompanyDocument,
};
