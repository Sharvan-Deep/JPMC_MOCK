const { AppError } = require('../utils/errors');

/**
 * Require the authenticated user to have one of the specified roles.
 * Must run after requireAuth.
 *
 * @param {...string} roles
 */
function requireRole(...roles) {
  return (req, _res, next) => {
    if (!req.user || !req.user.role) {
      return next(new AppError('Authentication required', 401, { code: 'AUTH_REQUIRED' }));
    }

    if (!roles.includes(req.user.role)) {
      return next(new AppError('Forbidden', 403, { code: 'FORBIDDEN' }));
    }

    next();
  };
}

module.exports = requireRole;
