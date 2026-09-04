const authService = require('../services/authService');
const { AppError } = require('../utils/errors');
const { validateLoginBody } = require('../validators/authValidator');
const {
  REFRESH_TOKEN_COOKIE,
  getRefreshCookieOptions,
  getRefreshCookieClearOptions,
} = require('../config/cookies');

async function login(req, res) {
  const validation = validateLoginBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const result = await authService.login(validation.data.email, validation.data.password);

  res.cookie(REFRESH_TOKEN_COOKIE, result.refreshToken, getRefreshCookieOptions());

  res.json({
    success: true,
    data: {
      accessToken: result.accessToken,
      user: result.user,
    },
  });
}

async function refresh(req, res) {
  const rawRefreshToken = req.cookies?.[REFRESH_TOKEN_COOKIE];
  const result = await authService.refreshSession(rawRefreshToken);

  res.cookie(REFRESH_TOKEN_COOKIE, result.refreshToken, getRefreshCookieOptions());

  res.json({
    success: true,
    data: {
      accessToken: result.accessToken,
    },
  });
}

async function logout(req, res) {
  const rawRefreshToken = req.cookies?.[REFRESH_TOKEN_COOKIE];
  await authService.logout(rawRefreshToken);

  res.clearCookie(REFRESH_TOKEN_COOKIE, getRefreshCookieClearOptions());

  res.json({
    success: true,
    message: 'Logged out successfully',
  });
}

async function me(req, res) {
  const user = await authService.getCurrentUser(req.user.id);

  res.json({
    success: true,
    data: user,
  });
}

module.exports = {
  login,
  refresh,
  logout,
  me,
};
