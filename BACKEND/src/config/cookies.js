const { getRefreshTokenExpiresMs } = require('./jwt');

const REFRESH_TOKEN_COOKIE = 'refreshToken';

function getRefreshCookieOptions() {
  const isProduction = process.env.NODE_ENV === 'production';

  return {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE === 'true' || isProduction,
    sameSite: process.env.COOKIE_SAME_SITE || 'lax',
    path: '/api/auth',
    maxAge: getRefreshTokenExpiresMs(),
  };
}

function getRefreshCookieClearOptions() {
  const { maxAge: _maxAge, ...options } = getRefreshCookieOptions();
  return options;
}

module.exports = {
  REFRESH_TOKEN_COOKIE,
  getRefreshCookieOptions,
  getRefreshCookieClearOptions,
};
