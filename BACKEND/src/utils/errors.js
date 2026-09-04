/**
 * Application error with HTTP status code for consistent API responses.
 */
class AppError extends Error {
  /**
   * @param {string} message
   * @param {number} [statusCode=500]
   * @param {{ code?: string, errors?: unknown[], details?: unknown }} [options]
   */
  constructor(message, statusCode = 500, options = {}) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = options.code;
    this.errors = options.errors;
    this.details = options.details;
    this.isOperational = true;
  }
}

module.exports = { AppError };
