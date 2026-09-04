const passwordResetService = require('../services/passwordResetService');
const { AppError } = require('../utils/errors');
const {
  validateForgotPasswordBody,
  validateResetPasswordBody,
} = require('../validators/passwordResetValidator');

async function forgotPassword(req, res) {
  const validation = validateForgotPasswordBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const result = await passwordResetService.requestPasswordReset(validation.data.email);

  res.json({
    success: true,
    message: result.message,
  });
}

async function resetPassword(req, res) {
  const validation = validateResetPasswordBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const result = await passwordResetService.resetPassword(
    validation.data.token,
    validation.data.password
  );

  res.json({
    success: true,
    message: result.message,
  });
}

module.exports = {
  forgotPassword,
  resetPassword,
};
