const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Normalize email for consistent storage and case-insensitive lookup.
 * @param {string} email
 * @returns {string}
 */
function normalizeEmail(email) {
  return String(email).trim().toLowerCase();
}

/**
 * @param {string} email
 * @returns {boolean}
 */
function isValidEmail(email) {
  if (!email || typeof email !== 'string') {
    return false;
  }

  const normalized = normalizeEmail(email);
  return normalized.length <= 255 && EMAIL_REGEX.test(normalized);
}

module.exports = {
  normalizeEmail,
  isValidEmail,
};
