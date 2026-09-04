const { User } = require('../models');
const authService = require('../services/authService');
const { AppError } = require('../utils/errors');

/**
 * Verify JWT access token and attach authenticated user context to the request.
 *
 * Sets:
 *   req.user = { id, _id, role }
 */
async function requireAuth(req, _res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return next(new AppError('Authentication required', 401, { code: 'AUTH_REQUIRED' }));
  }

  const token = authHeader.slice(7).trim();

  if (!token) {
    return next(new AppError('Authentication required', 401, { code: 'AUTH_REQUIRED' }));
  }

  try {
    const decoded = authService.verifyAccessToken(token);
    const user = await User.findById(decoded.sub).select('_id role isActive');

    if (!user || !user.isActive) {
      return next(new AppError('Authentication required', 401, { code: 'AUTH_REQUIRED' }));
    }

    if (decoded.role !== user.role) {
      return next(new AppError('Invalid or expired token', 401, { code: 'INVALID_TOKEN' }));
    }

    req.user = {
      id: user._id.toString(),
      _id: user._id,
      role: user.role,
    };

    next();
  } catch (_err) {
    return next(new AppError('Invalid or expired token', 401, { code: 'INVALID_TOKEN' }));
  }
}

module.exports = requireAuth;
