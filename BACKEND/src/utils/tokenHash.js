const crypto = require('crypto');

/**
 * Generate a cryptographically secure invitation token (raw value for email URL only).
 * @returns {string}
 */
function generateInvitationToken() {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * Hash a secure token before storing in MongoDB (SHA-256 lookup hash).
 * @param {string} token
 * @returns {string}
 */
function hashSecureToken(token) {
  return crypto.createHash('sha256').update(String(token)).digest('hex');
}

/** @deprecated Use hashSecureToken — kept for invitation module compatibility. */
function hashInvitationToken(token) {
  return hashSecureToken(token);
}

/**
 * Generate a cryptographically secure refresh token (raw value for HttpOnly cookie only).
 * @returns {string}
 */
function generateRefreshToken() {
  return crypto.randomBytes(48).toString('hex');
}

module.exports = {
  generateInvitationToken,
  generateRefreshToken,
  hashSecureToken,
  hashInvitationToken,
};
