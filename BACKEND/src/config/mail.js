const REQUIRED_MAIL_ENV = ['MAIL_HOST', 'MAIL_PORT', 'MAIL_USER', 'MAIL_PASSWORD'];

/**
 * Validate mail-related environment variables.
 * @returns {string[]} Missing variable names (empty if all present).
 */
function getMissingMailEnvVars() {
  return REQUIRED_MAIL_ENV.filter((key) => !process.env[key]);
}

/**
 * Nodemailer transport options derived from environment variables.
 * @throws {Error} When required variables are missing or MAIL_PORT is invalid.
 */
function getMailTransportOptions() {
  const missing = getMissingMailEnvVars();
  if (missing.length > 0) {
    throw new Error(
      `Missing required mail environment variables: ${missing.join(', ')}`
    );
  }

  const port = Number(process.env.MAIL_PORT);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error('MAIL_PORT must be a positive integer');
  }

  return {
    host: process.env.MAIL_HOST,
    port,
    secure: process.env.MAIL_SECURE === 'true',
    auth: {
      user: process.env.MAIL_USER,
      pass: process.env.MAIL_PASSWORD,
    },
  };
}

/**
 * Formatted "From" address using MAIL_FROM_NAME and MAIL_USER.
 */
function getMailFromAddress() {
  const options = getMailTransportOptions();
  const fromName = process.env.MAIL_FROM_NAME || 'Jaldhaara';

  return fromName
    ? `"${fromName}" <${options.auth.user}>`
    : options.auth.user;
}

module.exports = {
  getMissingMailEnvVars,
  getMailTransportOptions,
  getMailFromAddress,
};
