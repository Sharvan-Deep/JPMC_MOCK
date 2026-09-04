const { getFrontendUrl } = require('./invitationHelpers');

const DEFAULT_EXPIRY_HOURS = Number(process.env.PASSWORD_RESET_EXPIRES_HOURS) || 1;

function getPasswordResetCooldownMinutes() {
  const parsed = Number(process.env.PASSWORD_RESET_COOLDOWN_MINUTES);
  return Number.isFinite(parsed) ? parsed : 5;
}

/**
 * @returns {Date}
 */
function getPasswordResetExpiryDate() {
  return new Date(Date.now() + DEFAULT_EXPIRY_HOURS * 60 * 60 * 1000);
}

/**
 * @param {string} rawToken
 * @returns {string}
 */
function buildPasswordResetUrl(rawToken) {
  return `${getFrontendUrl()}/reset-password?token=${encodeURIComponent(rawToken)}`;
}

/**
 * @param {Date | undefined} referenceDate
 * @returns {boolean}
 */
function isWithinPasswordResetCooldown(referenceDate) {
  if (!referenceDate) {
    return false;
  }

  const cooldownMs = getPasswordResetCooldownMinutes() * 60 * 1000;
  return Date.now() - new Date(referenceDate).getTime() < cooldownMs;
}

module.exports = {
  DEFAULT_EXPIRY_HOURS,
  getPasswordResetCooldownMinutes,
  getPasswordResetExpiryDate,
  buildPasswordResetUrl,
  isWithinPasswordResetCooldown,
};
