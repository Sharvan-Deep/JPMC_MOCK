const bcrypt = require('bcryptjs');

const DEFAULT_SALT_ROUNDS = 12;
const PASSWORD_MIN_LENGTH = Number(process.env.PASSWORD_MIN_LENGTH) || 8;

/**
 * Validate password strength for account activation.
 * @param {string} password
 * @returns {{ valid: boolean, errors: string[] }}
 */
function validatePassword(password) {
  const errors = [];

  if (!password || typeof password !== 'string') {
    return { valid: false, errors: ['Password is required'] };
  }

  if (password.length < PASSWORD_MIN_LENGTH) {
    errors.push(`Password must be at least ${PASSWORD_MIN_LENGTH} characters`);
  }

  if (!/[A-Za-z]/.test(password)) {
    errors.push('Password must contain at least one letter');
  }

  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * @param {string} password
 * @returns {Promise<string>}
 */
async function hashPassword(password) {
  return bcrypt.hash(password, DEFAULT_SALT_ROUNDS);
}

/**
 * @param {string} password
 * @param {string} passwordHash
 * @returns {Promise<boolean>}
 */
async function verifyPassword(password, passwordHash) {
  return bcrypt.compare(password, passwordHash);
}

module.exports = {
  validatePassword,
  hashPassword,
  verifyPassword,
  PASSWORD_MIN_LENGTH,
};
