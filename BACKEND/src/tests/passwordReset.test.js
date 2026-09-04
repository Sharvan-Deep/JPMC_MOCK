/**
 * Password reset module tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-jwt-auth-module';
process.env.FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
process.env.PASSWORD_RESET_COOLDOWN_MINUTES = '0';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, PasswordResetToken, RefreshToken } = require('../models');
const authService = require('../services/authService');
const { hashPassword, verifyPassword } = require('../utils/password');
const { hashSecureToken } = require('../utils/tokenHash');
const { USER_ROLES } = require('../config/constants');
const { createTestRun } = require('./helpers/testIsolation');

const OLD_PASSWORD = 'SecurePass1';
const NEW_PASSWORD = 'NewSecure2';

const run = createTestRun();
const emails = {
  active: run.email('reset-active'),
  inactive: run.email('reset-inactive'),
  unknown: run.email('reset-unknown'),
};

let activeUser;
let inactiveUser;
let passwordResetService;
let originalSendPasswordResetEmail;
let resetEmailCalls;

before(async () => {
  await connectDatabase();

  const passwordHash = await hashPassword(OLD_PASSWORD);

  activeUser = await User.create({
    name: 'Reset Active User',
    email: emails.active,
    passwordHash,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  inactiveUser = await User.create({
    name: 'Reset Inactive User',
    email: emails.inactive,
    passwordHash,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: false,
    isEmailVerified: true,
  });

  const passwordResetEmailService = require('../services/passwordResetEmailService');
  originalSendPasswordResetEmail = passwordResetEmailService.sendPasswordResetEmail;
  resetEmailCalls = [];
  passwordResetEmailService.sendPasswordResetEmail = async (options) => {
    resetEmailCalls.push(options);
    return { success: true };
  };

  passwordResetService = require('../services/passwordResetService');
});

after(async () => {
  const passwordResetEmailService = require('../services/passwordResetEmailService');
  passwordResetEmailService.sendPasswordResetEmail = originalSendPasswordResetEmail;

  const testUserIds = [activeUser, inactiveUser].filter(Boolean).map((u) => u._id);

  if (testUserIds.length > 0) {
    await PasswordResetToken.deleteMany({ user: { $in: testUserIds } });
    await RefreshToken.deleteMany({ user: { $in: testUserIds } });
  }

  await User.deleteMany(run.emailFilter());
  await disconnectDatabase();
});

describe('Forgot password', () => {
  it('creates reset token and sends email for existing active user', async () => {
    resetEmailCalls.length = 0;
    await PasswordResetToken.deleteMany({ user: activeUser._id });

    const result = await passwordResetService.requestPasswordReset(emails.active);

    assert.equal(
      result.message,
      passwordResetService.GENERIC_FORGOT_PASSWORD_MESSAGE
    );
    assert.equal(resetEmailCalls.length, 1);
    assert.equal(resetEmailCalls[0].to, emails.active);

    const tokenRecord = await PasswordResetToken.findOne({ user: activeUser._id }).sort({
      createdAt: -1,
    });
    assert.ok(tokenRecord);
    assert.ok(tokenRecord.tokenHash);
    assert.equal(tokenRecord.usedAt, undefined);
  });

  it('returns same generic response for unknown email', async () => {
    const beforeCount = await PasswordResetToken.countDocuments();
    const result = await passwordResetService.requestPasswordReset(emails.unknown);

    assert.equal(
      result.message,
      passwordResetService.GENERIC_FORGOT_PASSWORD_MESSAGE
    );
    assert.equal(await PasswordResetToken.countDocuments(), beforeCount);
  });

  it('does not reveal inactive user existence', async () => {
    resetEmailCalls.length = 0;
    const result = await passwordResetService.requestPasswordReset(emails.inactive);

    assert.equal(
      result.message,
      passwordResetService.GENERIC_FORGOT_PASSWORD_MESSAGE
    );
    assert.equal(resetEmailCalls.length, 0);
  });

  it('does not store raw token', async () => {
    const records = await PasswordResetToken.find({ user: activeUser._id });
    for (const record of records) {
      assert.equal(record.tokenHash.length, 64);
      assert.notEqual(record.tokenHash, record.rawToken);
    }
  });
});

describe('Reset password', () => {
  it('resets password with valid token', async () => {
    const rawToken = `valid-reset-${run.id}`;
    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
    });

    const result = await passwordResetService.resetPassword(rawToken, NEW_PASSWORD);
    assert.equal(result.message, 'Password reset successfully.');

    const user = await User.findOne({ email: emails.active }).select('+passwordHash');
    assert.ok(await verifyPassword(NEW_PASSWORD, user.passwordHash));
    assert.equal(await verifyPassword(OLD_PASSWORD, user.passwordHash), false);
    assert.notEqual(user.passwordHash, NEW_PASSWORD);
  });

  it('rejects expired token', async () => {
    const rawToken = `expired-reset-${run.id}`;
    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() - 1000),
    });

    await assert.rejects(
      () => passwordResetService.resetPassword(rawToken, NEW_PASSWORD),
      (err) => err.statusCode === 400
    );
  });

  it('rejects used token', async () => {
    const rawToken = `used-reset-${run.id}`;
    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      usedAt: new Date(),
    });

    await assert.rejects(
      () => passwordResetService.resetPassword(rawToken, NEW_PASSWORD),
      (err) => err.statusCode === 400
    );
  });

  it('rejects invalid token', async () => {
    await assert.rejects(
      () => passwordResetService.resetPassword(`invalid-${run.id}`, NEW_PASSWORD),
      (err) => err.statusCode === 400
    );
  });

  it('revokes existing refresh sessions', async () => {
    const login = await authService.login(emails.active, NEW_PASSWORD);
    assert.ok(login.refreshToken);

    const rawToken = `refresh-revoke-${run.id}`;
    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
    });

    await passwordResetService.resetPassword(rawToken, 'AnotherPass3');

    const record = await RefreshToken.findOne({
      tokenHash: hashSecureToken(login.refreshToken),
    });
    assert.ok(record.revokedAt);
  });

  it('invalidates other reset tokens for the user', async () => {
    const rawToken = `primary-reset-${run.id}`;
    const otherToken = `other-reset-${run.id}`;

    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(otherToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
    });

    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
    });

    await passwordResetService.resetPassword(rawToken, 'FinalPass4');

    const otherRecord = await PasswordResetToken.findOne({
      tokenHash: hashSecureToken(otherToken),
    });
    assert.ok(otherRecord.usedAt);
  });

  it('prevents token reuse', async () => {
    const rawToken = `reuse-reset-${run.id}`;
    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
    });

    await passwordResetService.resetPassword(rawToken, 'ReusePass5');

    await assert.rejects(
      () => passwordResetService.resetPassword(rawToken, 'ReusePass6'),
      (err) => err.statusCode === 400
    );
  });

  it('allows login with new password after reset', async () => {
    const rawToken = `login-reset-${run.id}`;
    await PasswordResetToken.create({
      user: activeUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
    });

    const loginPassword = 'LoginPass7';
    await passwordResetService.resetPassword(rawToken, loginPassword);

    const login = await authService.login(emails.active, loginPassword);
    assert.ok(login.accessToken);
    assert.equal(login.user.email, emails.active);
  });
});
