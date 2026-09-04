const { INVITATION_STATUSES } = require('../config/constants');

const DEFAULT_EXPIRY_HOURS = Number(process.env.INVITATION_EXPIRY_HOURS) || 72;

function getResendCooldownMinutes() {
  const parsed = Number(process.env.INVITATION_RESEND_COOLDOWN_MINUTES);
  return Number.isFinite(parsed) ? parsed : 5;
}

/**
 * @returns {Date}
 */
function getInvitationExpiryDate() {
  return new Date(Date.now() + DEFAULT_EXPIRY_HOURS * 60 * 60 * 1000);
}

/**
 * @returns {string}
 */
function getFrontendUrl() {
  const url = process.env.FRONTEND_URL;
  if (!url) {
    throw new Error('FRONTEND_URL is not defined in environment variables');
  }
  return url.replace(/\/$/, '');
}

/**
 * Build activation URL for invitation emails. Raw token is only used here and in client requests.
 * @param {string} rawToken
 * @returns {string}
 */
function buildActivationUrl(rawToken) {
  return `${getFrontendUrl()}/activate?token=${encodeURIComponent(rawToken)}`;
}

/**
 * @param {import('mongoose').Document | object} invitation
 * @returns {object}
 */
function toPublicInvitation(invitation) {
  const obj = invitation.toObject ? invitation.toObject() : { ...invitation };
  delete obj.tokenHash;
  return obj;
}

/**
 * Mark invitation as expired in DB when past expiresAt (explicit app-level check).
 * @param {import('mongoose').Document} invitation
 */
async function markExpiredIfNeeded(invitation) {
  if (
    invitation.status === INVITATION_STATUSES.PENDING &&
    invitation.expiresAt &&
    invitation.expiresAt.getTime() <= Date.now()
  ) {
    invitation.status = INVITATION_STATUSES.EXPIRED;
    await invitation.save();
  }
}

/**
 * Basic cooldown to prevent rapid duplicate invite/resend emails.
 * @param {Date | undefined} referenceDate
 */
function isWithinResendCooldown(referenceDate) {
  if (!referenceDate) {
    return false;
  }

  const cooldownMs = getResendCooldownMinutes() * 60 * 1000;
  return Date.now() - new Date(referenceDate).getTime() < cooldownMs;
}

module.exports = {
  DEFAULT_EXPIRY_HOURS,
  getResendCooldownMinutes,
  getInvitationExpiryDate,
  getFrontendUrl,
  buildActivationUrl,
  toPublicInvitation,
  markExpiredIfNeeded,
  isWithinResendCooldown,
};
