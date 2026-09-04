const { AppError } = require('../utils/errors');

/**
 * Central Express error handler for API responses.
 * Handles AppError (including AI gateway codes/details), Mongoose errors,
 * and generic errors that set `statusCode`.
 */
// eslint-disable-next-line no-unused-vars
function errorHandler(err, _req, res, _next) {
  if (err instanceof AppError) {
    if (err.statusCode >= 500) {
      console.error(err);
    }

    return res.status(err.statusCode).json({
      success: false,
      message: err.message,
      ...(err.code ? { code: err.code } : {}),
      ...(err.errors ? { errors: err.errors } : {}),
      ...(err.details ? { details: err.details } : {}),
    });
  }

  if (err.name === 'ValidationError') {
    const errors = Object.values(err.errors || {}).map((e) => e.message);
    return res.status(400).json({
      success: false,
      message: 'Validation failed',
      errors,
    });
  }

  if (err.code === 11000) {
    return res.status(409).json({
      success: false,
      message: 'Duplicate record',
    });
  }

  if (err.message === 'Only CSV files are allowed') {
    return res.status(400).json({
      success: false,
      message: err.message,
    });
  }

  const statusCode = err.statusCode || 500;

  if (statusCode >= 500) {
    console.error('Unhandled error:', err.message || err);
  }

  return res.status(statusCode).json({
    success: false,
    message: statusCode >= 500 ? 'Internal server error' : err.message || 'Internal server error',
  });
}

module.exports = errorHandler;
