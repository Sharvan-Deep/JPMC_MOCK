/**
 * CLI script to verify SMTP configuration and send a test email.
 *
 * Usage:
 *   node src/scripts/testMail.js [recipient@example.com]
 *   npm run test:mail -- recipient@example.com
 *
 * Environment:
 *   MAIL_HOST, MAIL_PORT, MAIL_SECURE, MAIL_USER, MAIL_PASSWORD, MAIL_FROM_NAME
 *   MAIL_TEST_RECIPIENT — used when no CLI recipient is provided
 */
require('dotenv').config();

const { getMissingMailEnvVars } = require('../config/mail');
const { getTransporter, sendEmail } = require('../services/mailService');

async function main() {
  const recipient =
    process.argv[2] || process.env.MAIL_TEST_RECIPIENT;

  const missing = getMissingMailEnvVars();
  if (missing.length > 0) {
    console.error(
      `Mail configuration error: missing environment variables — ${missing.join(', ')}`
    );
    process.exit(1);
  }

  try {
    const transport = getTransporter();
    await transport.verify();
    console.log('SMTP transporter verified successfully');
  } catch (err) {
    console.error(
      'SMTP transporter verification failed:',
      err instanceof Error ? err.message : err
    );
    process.exit(1);
  }

  if (!recipient) {
    console.error(
      'No recipient provided. Pass an email as a CLI argument or set MAIL_TEST_RECIPIENT.'
    );
    process.exit(1);
  }

  const result = await sendEmail({
    to: recipient,
    subject: 'Jaldhaara — mail service test',
    text: 'This is a test email from the Jaldhaara backend mail service.',
    html: '<p>This is a <strong>test email</strong> from the Jaldhaara backend mail service.</p>',
  });

  if (result.success) {
    console.log(`Test email sent to ${recipient}`);
    console.log(`Message ID: ${result.messageId}`);
    process.exit(0);
  }

  console.error('Failed to send test email:', result.error);
  process.exit(1);
}

main().catch((err) => {
  console.error('Unexpected error:', err instanceof Error ? err.message : err);
  process.exit(1);
});
