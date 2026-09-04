const { User, PasswordResetToken, RefreshToken } = require('../models');
const { AppError } = require('../utils/errors');
const { normalizeEmail } = require('../utils/email');
const { hashPassword } = require('../utils/password');
const { generateInvitationToken, hashSecureToken } = require('../utils/tokenHash');
const {
  getPasswordResetExpiryDate,
  isWithinPasswordResetCooldown,
} = require('../utils/passwordResetHelpers');
const { sendPasswordResetEmail } = require('./passwordResetEmailService');

const GENERIC_FORGOT_PASSWORD_MESSAGE =
  'If the account exists, a password reset link has been sent.';

/**
 * @param {string} email
 */
async function requestPasswordReset(email) {
  const normalizedEmail = normalizeEmail(email);
  const user = await User.findOne({ email: normalizedEmail, isActive: true }).select(
    '+passwordHash'
  );

  if (!user || !user.passwordHash) {
    return { message: GENERIC_FORGOT_PASSWORD_MESSAGE };
  }

  const latestToken = await PasswordResetToken.findOne({
    user: user._id,
    usedAt: { $exists: false },
  }).sort({ createdAt: -1 });

  if (latestToken && isWithinPasswordResetCooldown(latestToken.createdAt)) {
    return { message: GENERIC_FORGOT_PASSWORD_MESSAGE };
  }

  await PasswordResetToken.updateMany(
    { user: user._id, usedAt: { $exists: false } },
    { usedAt: new Date() }
  );

  const rawToken = generateInvitationToken();
  const tokenHash = hashSecureToken(rawToken);

  await PasswordResetToken.create({
    user: user._id,
    tokenHash,
    expiresAt: getPasswordResetExpiryDate(),
  });

  const emailResult = await sendPasswordResetEmail({
    to: user.email,
    name: user.name,
    rawToken,
  });

  if (!emailResult.success) {
    console.error('Password reset email failed to send');
  }

  return { message: GENERIC_FORGOT_PASSWORD_MESSAGE };
}

/**
 * @param {string} rawToken
 */
async function findActiveResetToken(rawToken) {
  const tokenHash = hashSecureToken(rawToken);
  return PasswordResetToken.findOne({ tokenHash });
}

/**
 * @param {string} token
 * @param {string} password
 */
async function resetPassword(token, password) {
  const resetRecord = await findActiveResetToken(token);

  if (!resetRecord || resetRecord.usedAt) {
    throw new AppError('Invalid or expired reset token', 400, {
      code: 'INVALID_RESET_TOKEN',
    });
  }

  if (resetRecord.expiresAt.getTime() <= Date.now()) {
    resetRecord.usedAt = new Date();
    await resetRecord.save();
    throw new AppError('Invalid or expired reset token', 400, {
      code: 'INVALID_RESET_TOKEN',
    });
  }

  const user = await User.findById(resetRecord.user).select('+passwordHash');

  if (!user || !user.isActive) {
    throw new AppError('Invalid or expired reset token', 400, {
      code: 'INVALID_RESET_TOKEN',
    });
  }

  user.passwordHash = await hashPassword(password);
  await user.save();

  resetRecord.usedAt = new Date();
  await resetRecord.save();

  await PasswordResetToken.updateMany(
    { user: user._id, usedAt: { $exists: false } },
    { usedAt: new Date() }
  );

  await RefreshToken.updateMany(
    { user: user._id, revokedAt: { $exists: false } },
    { revokedAt: new Date() }
  );

  return { message: 'Password reset successfully.' };
}

module.exports = {
  requestPasswordReset,
  resetPassword,
  findActiveResetToken,
  GENERIC_FORGOT_PASSWORD_MESSAGE,
};
