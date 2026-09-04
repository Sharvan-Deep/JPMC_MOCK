const { sendEmail } = require('./mailService');
const {
  buildPasswordResetUrl,
  DEFAULT_EXPIRY_HOURS,
} = require('../utils/passwordResetHelpers');

const SUPPORT_EMAIL = process.env.SUPPORT_EMAIL || 'support@jaldhaara.org';

/**
 * @param {{ name: string, resetUrl: string, expiresHours: number }} params
 * @returns {{ subject: string, text: string, html: string }}
 */
function buildPasswordResetEmailContent({ name, resetUrl, expiresHours }) {
  const subject = 'Reset your Jaldhaara password';

  const text = [
    `Hello ${name},`,
    '',
    'We received a request to reset your Jaldhaara Foundation account password.',
    'Use the link below to choose a new password:',
    '',
    resetUrl,
    '',
    `This link expires in ${expiresHours} hour(s) and can only be used once.`,
    '',
    'If you did not request a password reset, you can safely ignore this email.',
    `For help, contact ${SUPPORT_EMAIL}.`,
    '',
    '— Jaldhaara Foundation',
  ].join('\n');

  const html = `
    <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #1a1a1a;">
      <h2 style="color: #0b5cab;">Jaldhaara Foundation</h2>
      <p>Hello ${escapeHtml(name)},</p>
      <p>We received a request to reset your <strong>Jaldhaara</strong> account password.</p>
      <p>
        <a href="${escapeHtml(resetUrl)}" style="display:inline-block;padding:10px 16px;background:#0b5cab;color:#fff;text-decoration:none;border-radius:4px;">
          Reset your password
        </a>
      </p>
      <p style="font-size: 14px; color: #555;">This link expires in ${expiresHours} hour(s) and can only be used once.</p>
      <p style="font-size: 14px; color: #555;">If you did not request this, you can safely ignore this email.</p>
      <p style="font-size: 14px; color: #555;">Need help? Contact <a href="mailto:${escapeHtml(SUPPORT_EMAIL)}">${escapeHtml(SUPPORT_EMAIL)}</a>.</p>
      <p>— Jaldhaara Foundation</p>
    </div>
  `;

  return { subject, text, html };
}

/**
 * @param {string} value
 * @returns {string}
 */
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Send password reset email via the shared mail service.
 * Never logs the raw token.
 *
 * @param {{ to: string, name: string, rawToken: string }} params
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
async function sendPasswordResetEmail({ to, name, rawToken }) {
  const resetUrl = buildPasswordResetUrl(rawToken);
  const { subject, text, html } = buildPasswordResetEmailContent({
    name,
    resetUrl,
    expiresHours: DEFAULT_EXPIRY_HOURS,
  });

  const result = await sendEmail({ to, subject, text, html });

  if (!result.success) {
    return { success: false, error: result.error };
  }

  return { success: true };
}

module.exports = {
  buildPasswordResetEmailContent,
  sendPasswordResetEmail,
};
