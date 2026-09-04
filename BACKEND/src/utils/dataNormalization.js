/**
 * Data normalization utilities for CSV import and company deduplication.
 */

/**
 * Build a normalized company name key for import matching.
 *
 * LIMITATION: Matching is exact on normalized name (trim + lowercase).
 * Companies with slightly different spellings will create separate records.
 * No fuzzy matching is performed.
 */
function buildCompanyNameKey(companyName) {
  if (!companyName || typeof companyName !== 'string') {
    return '';
  }
  return companyName.trim().toLowerCase();
}

/**
 * Parse a numeric CSV value to a finite number.
 * Returns fallback (default 0) for empty, null, or non-numeric values.
 */
function parseNumeric(value, fallback = 0) {
  if (value === null || value === undefined) {
    return fallback;
  }

  const trimmed = String(value).trim();
  if (trimmed === '' || trimmed.toLowerCase() === 'na' || trimmed === '-') {
    return fallback;
  }

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : fallback;
}

/**
 * Parse an integer CSV value.
 */
function parseInteger(value, fallback = 0) {
  const num = parseNumeric(value, fallback);
  return Math.max(0, Math.trunc(num));
}

/**
 * Normalize a delimited string field into a deduplicated string array.
 *
 * The primary CSV is expected to use pipe (|) or semicolon (;) delimiters for
 * multi-value fields. Comma is also supported as a fallback delimiter when
 * the value does not look like a single token.
 *
 * Examples:
 *   "Maharashtra|Karnataka"  → ["Maharashtra", "Karnataka"]
 *   "2019-20; 2020-21"       → ["2019-20", "2020-21"]
 */
function parseDelimitedArray(value) {
  if (value === null || value === undefined) {
    return [];
  }

  const trimmed = String(value).trim();
  if (trimmed === '' || trimmed.toLowerCase() === 'na' || trimmed === '-') {
    return [];
  }

  let parts;
  if (trimmed.includes('|')) {
    parts = trimmed.split('|');
  } else if (trimmed.includes(';')) {
    parts = trimmed.split(';');
  } else if (trimmed.includes(',')) {
    parts = trimmed.split(',');
  } else {
    parts = [trimmed];
  }

  const seen = new Set();
  const result = [];

  for (const part of parts) {
    const cleaned = part.trim();
    if (!cleaned) continue;
    const key = cleaned.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      result.push(cleaned);
    }
  }

  return result;
}

/**
 * Parse a date string from CSV into a Date object.
 * Supports ISO dates (YYYY-MM-DD) and common slash formats.
 * Returns null for empty or unparseable values.
 */
function parseDate(value) {
  if (value === null || value === undefined) {
    return null;
  }

  const trimmed = String(value).trim();
  if (trimmed === '' || trimmed.toLowerCase() === 'na' || trimmed === '-') {
    return null;
  }

  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Normalize a free-text field; returns empty string for null-like values.
 */
function parseText(value) {
  if (value === null || value === undefined) {
    return '';
  }

  const trimmed = String(value).trim();
  if (trimmed.toLowerCase() === 'na' || trimmed === '-') {
    return '';
  }

  return trimmed;
}

module.exports = {
  buildCompanyNameKey,
  parseNumeric,
  parseInteger,
  parseDelimitedArray,
  parseDate,
  parseText,
};
