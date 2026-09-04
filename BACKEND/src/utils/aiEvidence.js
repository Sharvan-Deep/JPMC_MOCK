/**
 * Copy AI evidence objects without inventing missing fields.
 * @param {unknown} item
 */
function normalizeEvidence(item) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    return null;
  }

  const evidence = {};
  const fields = [
    'company',
    'financial_year',
    'document_type',
    'document_version',
    'page',
    'source_url',
    'relevant_source_text',
    'document_hash',
  ];

  for (const field of fields) {
    if (item[field] !== undefined && item[field] !== null && item[field] !== '') {
      evidence[field] = item[field];
    }
  }

  return Object.keys(evidence).length > 0 ? evidence : null;
}

/**
 * @param {unknown} payload
 * @returns {object[]}
 */
function extractEvidence(payload) {
  if (!payload) {
    return [];
  }

  const buckets = [];

  if (Array.isArray(payload)) {
    buckets.push(...payload);
  } else if (typeof payload === 'object') {
    for (const key of ['evidence', 'evidence_used', 'evidence_sources']) {
      if (Array.isArray(payload[key])) {
        buckets.push(...payload[key]);
      }
    }
  }

  return buckets.map(normalizeEvidence).filter(Boolean);
}

/**
 * @param {unknown} value
 * @returns {string[]}
 */
function asStringArray(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => (typeof item === 'string' ? item : null))
    .filter(Boolean);
}

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null);
}

module.exports = {
  normalizeEvidence,
  extractEvidence,
  asStringArray,
  firstDefined,
};
