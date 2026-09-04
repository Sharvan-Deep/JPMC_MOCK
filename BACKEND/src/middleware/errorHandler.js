const { AppError } = require('../utils/errors');

/**
 * Central Express error handler.
 */
// eslint-disable-next-line no-unused-vars
function errorHandler(err, _req, res, _next) {
  if (err instanceof AppError) {
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

  console.error('Unhandled error:', err.message);

  return res.status(500).json({
    success: false,
    message: 'Internal server error',
  });
}

module.exports = errorHandler;
