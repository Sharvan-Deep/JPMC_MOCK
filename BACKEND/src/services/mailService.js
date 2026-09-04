const nodemailer = require('nodemailer');
const {
  getMailTransportOptions,
  getMailFromAddress,
} = require('../config/mail');

let transporter = null;

/**
 * Return a reusable Nodemailer transporter (lazy singleton).
 * @throws {Error} When mail environment variables are invalid or missing.
 */
function getTransporter() {
  if (!transporter) {
    transporter = nodemailer.createTransport(getMailTransportOptions());
  }
  return transporter;
}

/**
 * Reset the cached transporter (useful for tests or config changes).
 */
function resetTransporter() {
  transporter = null;
}

/**
 * @param {{ to?: string, subject?: string, text?: string, html?: string }} options
 * @returns {string[]} Validation error messages.
 */
function validateSendOptions({ to, subject, text, html }) {
  const errors = [];

  if (!to || typeof to !== 'string' || !to.trim()) {
    errors.push('to is required');
  }
  if (!subject || typeof subject !== 'string' || !subject.trim()) {
    errors.push('subject is required');
  }
  if (!text && !html) {
    errors.push('text or html is required');
  }

  return errors;
}

/**
 * Send a transactional email via the configured SMTP transport.
 *
 * @param {{ to: string, subject: string, text?: string, html?: string }} options
 * @returns {Promise<{ success: true, messageId: string } | { success: false, error: string }>}
 */
async function sendEmail({ to, subject, text, html }) {
  const validationErrors = validateSendOptions({ to, subject, text, html });
  if (validationErrors.length > 0) {
    return { success: false, error: validationErrors.join('; ') };
  }

  try {
    const transport = getTransporter();
    const info = await transport.sendMail({
      from: getMailFromAddress(),
      to: to.trim(),
      subject: subject.trim(),
      text,
      html,
    });

    return { success: true, messageId: info.messageId };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Failed to send email',
    };
  }
}

module.exports = {
  getTransporter,
  resetTransporter,
  sendEmail,
};
