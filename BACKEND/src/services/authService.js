const jwt = require('jsonwebtoken');
const { User, RefreshToken } = require('../models');
const { AppError } = require('../utils/errors');
const { normalizeEmail } = require('../utils/email');
const { verifyPassword } = require('../utils/password');
const { generateRefreshToken, hashSecureToken } = require('../utils/tokenHash');
const { toSafeUser } = require('../utils/userSerializer');
const {
  getAccessTokenSecret,
  getAccessTokenExpiresIn,
  getRefreshTokenExpiryDate,
} = require('../config/jwt');

const INVALID_CREDENTIALS_MESSAGE = 'Invalid email or password';

/**
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 * @returns {string}
 */
function createAccessToken(user) {
  return jwt.sign(
    {
      sub: user._id.toString(),
      role: user.role,
    },
    getAccessTokenSecret(),
    { expiresIn: getAccessTokenExpiresIn() }
  );
}

/**
 * @param {string} token
 * @returns {{ sub: string, role: string }}
 */
function verifyAccessToken(token) {
  return jwt.verify(token, getAccessTokenSecret());
}

/**
 * @param {import('mongoose').Types.ObjectId} userId
 * @returns {Promise<{ rawToken: string, record: import('mongoose').Document }>}
 */
async function issueRefreshToken(userId) {
  const rawToken = generateRefreshToken();
  const tokenHash = hashSecureToken(rawToken);

  const record = await RefreshToken.create({
    user: userId,
    tokenHash,
    expiresAt: getRefreshTokenExpiryDate(),
  });

  return { rawToken, record };
}

/**
 * @param {string} email
 * @param {string} password
 */
async function login(email, password) {
  const normalizedEmail = normalizeEmail(email);

  const user = await User.findOne({ email: normalizedEmail }).select('+passwordHash');

  if (!user || !user.passwordHash) {
    throw new AppError(INVALID_CREDENTIALS_MESSAGE, 401, { code: 'INVALID_CREDENTIALS' });
  }

  if (!user.isActive) {
    throw new AppError(INVALID_CREDENTIALS_MESSAGE, 401, { code: 'INVALID_CREDENTIALS' });
  }

  const passwordValid = await verifyPassword(password, user.passwordHash);

  if (!passwordValid) {
    throw new AppError(INVALID_CREDENTIALS_MESSAGE, 401, { code: 'INVALID_CREDENTIALS' });
  }

  user.lastLoginAt = new Date();
  await user.save();

  const accessToken = createAccessToken(user);
  const { rawToken: refreshToken } = await issueRefreshToken(user._id);

  return {
    accessToken,
    refreshToken,
    user: toSafeUser(user),
  };
}

/**
 * @param {string | undefined} rawRefreshToken
 */
async function refreshSession(rawRefreshToken) {
  if (!rawRefreshToken) {
    throw new AppError('Refresh token required', 401, { code: 'REFRESH_REQUIRED' });
  }

  const tokenHash = hashSecureToken(rawRefreshToken);
  const tokenRecord = await RefreshToken.findOne({ tokenHash });

  if (!tokenRecord || tokenRecord.revokedAt) {
    throw new AppError('Invalid refresh token', 401, { code: 'INVALID_REFRESH_TOKEN' });
  }

  if (tokenRecord.expiresAt.getTime() <= Date.now()) {
    tokenRecord.revokedAt = new Date();
    await tokenRecord.save();
    throw new AppError('Refresh token expired', 401, { code: 'REFRESH_EXPIRED' });
  }

  const user = await User.findById(tokenRecord.user);

  if (!user || !user.isActive) {
    tokenRecord.revokedAt = new Date();
    await tokenRecord.save();
    throw new AppError('Invalid refresh token', 401, { code: 'INVALID_REFRESH_TOKEN' });
  }

  tokenRecord.revokedAt = new Date();
  await tokenRecord.save();

  const accessToken = createAccessToken(user);
  const { rawToken: refreshToken } = await issueRefreshToken(user._id);

  return {
    accessToken,
    refreshToken,
  };
}

/**
 * @param {string | undefined} rawRefreshToken
 */
async function logout(rawRefreshToken) {
  if (!rawRefreshToken) {
    return;
  }

  const tokenHash = hashSecureToken(rawRefreshToken);
  const tokenRecord = await RefreshToken.findOne({ tokenHash });

  if (tokenRecord && !tokenRecord.revokedAt) {
    tokenRecord.revokedAt = new Date();
    await tokenRecord.save();
  }
}

/**
 * @param {string} userId
 */
async function getCurrentUser(userId) {
  const user = await User.findById(userId);

  if (!user || !user.isActive) {
    throw new AppError('User not found', 404, { code: 'USER_NOT_FOUND' });
  }

  return toSafeUser(user);
}

module.exports = {
  createAccessToken,
  verifyAccessToken,
  login,
  refreshSession,
  logout,
  getCurrentUser,
  INVALID_CREDENTIALS_MESSAGE,
};
