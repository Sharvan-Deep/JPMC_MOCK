const { normalizeEmail, isValidEmail } = require('../utils/email');

/**
 * @param {{ email?: string, password?: string }} body
 * @returns {{ valid: boolean, errors: string[], data?: { email: string, password: string } }}
 */
function validateLoginBody(body) {
  const errors = [];

  if (!body?.email || typeof body.email !== 'string' || !body.email.trim()) {
    errors.push('Email is required');
  } else if (!isValidEmail(body.email)) {
    errors.push('Invalid email address');
  }

  if (!body?.password || typeof body.password !== 'string' || !body.password) {
    errors.push('Password is required');
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      email: normalizeEmail(body.email),
      password: body.password,
    },
  };
}

module.exports = {
  validateLoginBody,
};
