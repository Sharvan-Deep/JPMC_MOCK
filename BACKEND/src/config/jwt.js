/**
 * JWT and refresh-token configuration from environment variables.
 */

function parseDurationToMs(duration, fallbackMs) {
  if (!duration || typeof duration !== 'string') {
    return fallbackMs;
  }

  const match = /^(\d+)([smhd])$/i.exec(duration.trim());
  if (!match) {
    return fallbackMs;
  }

  const value = Number(match[1]);
  const unit = match[2].toLowerCase();
  const multipliers = { s: 1000, m: 60_000, h: 3_600_000, d: 86_400_000 };

  return value * multipliers[unit];
}

function getAccessTokenSecret() {
  const secret = process.env.JWT_ACCESS_SECRET || process.env.JWT_SECRET;
  if (!secret) {
    throw new Error('JWT_ACCESS_SECRET is not defined in environment variables');
  }
  return secret;
}

function getAccessTokenExpiresIn() {
  return process.env.JWT_ACCESS_EXPIRES_IN || '15m';
}

function getRefreshTokenExpiresIn() {
  return process.env.JWT_REFRESH_EXPIRES_IN || '7d';
}

function getRefreshTokenExpiresMs() {
  return parseDurationToMs(getRefreshTokenExpiresIn(), 7 * 86_400_000);
}

function getRefreshTokenExpiryDate() {
  return new Date(Date.now() + getRefreshTokenExpiresMs());
}

const REFRESH_TOKEN_COOKIE = 'refreshToken';

module.exports = {
  getAccessTokenSecret,
  getAccessTokenExpiresIn,
  getRefreshTokenExpiresIn,
  getRefreshTokenExpiresMs,
  getRefreshTokenExpiryDate,
  REFRESH_TOKEN_COOKIE,
};
