const { normalizeEmail, isValidEmail } = require('../utils/email');
const { validatePassword } = require('../utils/password');

/**
 * @param {{ email?: string }} body
 */
function validateForgotPasswordBody(body) {
  const errors = [];

  if (!body?.email || typeof body.email !== 'string' || !body.email.trim()) {
    errors.push('Email is required');
  } else if (!isValidEmail(body.email)) {
    errors.push('Invalid email address');
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      email: normalizeEmail(body.email),
    },
  };
}

/**
 * @param {{ token?: string, password?: string }} body
 */
function validateResetPasswordBody(body) {
  const errors = [];

  if (!body?.token || typeof body.token !== 'string' || !body.token.trim()) {
    errors.push('Token is required');
  }

  const passwordResult = validatePassword(body?.password);
  if (!passwordResult.valid) {
    errors.push(...passwordResult.errors);
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      token: body.token.trim(),
      password: body.password,
    },
  };
}

module.exports = {
  validateForgotPasswordBody,
  validateResetPasswordBody,
};
