/**
 * Development-only script to create or reset a local Admin account.
 *
 * Usage:
 *   ALLOW_ADMIN_BOOTSTRAP=true npm run bootstrap:admin
 *
 * Required environment variables:
 *   ALLOW_ADMIN_BOOTSTRAP=true
 *   ADMIN_EMAIL
 *   ADMIN_PASSWORD
 *   ADMIN_NAME
 *
 * Never expose this through HTTP. Local development use only.
 */
require('dotenv').config();

const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User } = require('../models');
const { USER_ROLES } = require('../config/constants');
const { normalizeEmail, isValidEmail } = require('../utils/email');
const { hashPassword, validatePassword } = require('../utils/password');

function fail(message) {
  console.error(`Bootstrap failed: ${message}`);
  process.exit(1);
}

function isBootstrapAllowed() {
  return process.env.ALLOW_ADMIN_BOOTSTRAP === 'true';
}

function validateConfig() {
  if (!isBootstrapAllowed()) {
    fail('ALLOW_ADMIN_BOOTSTRAP must be set to "true" to run this script');
  }

  const email = process.env.ADMIN_EMAIL;
  const password = process.env.ADMIN_PASSWORD;
  const name = process.env.ADMIN_NAME;

  if (!email || !String(email).trim()) {
    fail('ADMIN_EMAIL is required');
  }

  if (!isValidEmail(email)) {
    fail('ADMIN_EMAIL is invalid');
  }

  if (!password || !String(password)) {
    fail('ADMIN_PASSWORD is required');
  }

  const passwordValidation = validatePassword(password);
  if (!passwordValidation.valid) {
    fail(`ADMIN_PASSWORD is invalid: ${passwordValidation.errors.join('; ')}`);
  }

  if (!name || !String(name).trim()) {
    fail('ADMIN_NAME is required');
  }

  return {
    email: normalizeEmail(email),
    password,
    name: String(name).trim(),
  };
}

async function bootstrapAdmin() {
  const config = validateConfig();

  await connectDatabase();

  const passwordHash = await hashPassword(config.password);
  let user = await User.findOne({ email: config.email }).select('+passwordHash');
  let action;

  if (!user) {
    user = await User.create({
      name: config.name,
      email: config.email,
      passwordHash,
      role: USER_ROLES.ADMIN,
      isActive: true,
      isEmailVerified: true,
    });
    action = 'created';
  } else {
    user.name = config.name;
    user.passwordHash = passwordHash;
    user.role = USER_ROLES.ADMIN;
    user.isActive = true;
    user.isEmailVerified = true;
    await user.save();
    action = 'updated';
  }

  console.log('Bootstrap succeeded');
  console.log(`Action: ${action}`);
  console.log(`Email: ${user.email}`);
  console.log(`Role: ${user.role}`);

  await disconnectDatabase();
}

bootstrapAdmin().catch((err) => {
  console.error('Bootstrap failed:', err instanceof Error ? err.message : err);
  disconnectDatabase().finally(() => process.exit(1));
});
