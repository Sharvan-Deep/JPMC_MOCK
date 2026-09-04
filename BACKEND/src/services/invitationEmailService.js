const { sendEmail } = require('./mailService');
const {
  buildActivationUrl,
  DEFAULT_EXPIRY_HOURS,
} = require('../utils/invitationHelpers');

const SUPPORT_EMAIL = process.env.SUPPORT_EMAIL || 'support@jaldhaara.org';

/**
 * @param {{ name: string, activationUrl: string, expiresHours: number }} params
 * @returns {{ subject: string, text: string, html: string }}
 */
function buildInvitationEmailContent({ name, activationUrl, expiresHours }) {
  const subject = 'You are invited to join Jaldhaara';

  const text = [
    `Hello ${name},`,
    '',
    'You have been invited to join the Jaldhaara Foundation platform.',
    'Please activate your account and set your password using the link below:',
    '',
    activationUrl,
    '',
    `This invitation link expires in ${expiresHours} hours.`,
    '',
    `If you did not expect this invitation, you can ignore this email.`,
    `For help, contact ${SUPPORT_EMAIL}.`,
    '',
    '— Jaldhaara Foundation',
  ].join('\n');

  const html = `
    <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #1a1a1a;">
      <h2 style="color: #0b5cab;">Jaldhaara Foundation</h2>
      <p>Hello ${escapeHtml(name)},</p>
      <p>You have been invited to join the <strong>Jaldhaara</strong> platform.</p>
      <p>Please activate your account and choose your password:</p>
      <p>
        <a href="${escapeHtml(activationUrl)}" style="display:inline-block;padding:10px 16px;background:#0b5cab;color:#fff;text-decoration:none;border-radius:4px;">
          Activate your account
        </a>
      </p>
      <p style="font-size: 14px; color: #555;">This link expires in ${expiresHours} hours.</p>
      <p style="font-size: 14px; color: #555;">If you did not expect this invitation, you can safely ignore this email.</p>
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
 * Send invitation email via the shared mail service.
 * Never logs the raw token.
 *
 * @param {{ to: string, name: string, rawToken: string }} params
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
async function sendInvitationEmail({ to, name, rawToken }) {
  const activationUrl = buildActivationUrl(rawToken);
  const { subject, text, html } = buildInvitationEmailContent({
    name,
    activationUrl,
    expiresHours: DEFAULT_EXPIRY_HOURS,
  });

  const result = await sendEmail({ to, subject, text, html });

  if (!result.success) {
    return { success: false, error: result.error };
  }

  return { success: true };
}

module.exports = {
  buildInvitationEmailContent,
  sendInvitationEmail,
};
