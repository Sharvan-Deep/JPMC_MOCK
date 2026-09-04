const mongoose = require('mongoose');
const { AppError } = require('../utils/errors');
const { USER_ROLES } = require('../config/constants');
const requireRole = require('./requireRole');

/**
 * Require an authenticated admin user.
 * Must be used after requireAuth.
 */
const requireAdmin = requireRole(USER_ROLES.ADMIN);

/**
 * Validate MongoDB ObjectId route parameters.
 * @param {string} paramName
 */
function validateObjectIdParam(paramName) {
  return (req, _res, next) => {
    const value = req.params[paramName];

    if (!value || !mongoose.Types.ObjectId.isValid(value)) {
      return next(new AppError(`Invalid ${paramName}`, 400, { code: 'INVALID_ID' }));
    }

    next();
  };
}

module.exports = {
  requireAdmin,
  validateObjectIdParam,
};
