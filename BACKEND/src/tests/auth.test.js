/**
 * JWT + email/password authentication tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-jwt-auth-module';
process.env.JWT_ACCESS_EXPIRES_IN = '15m';
process.env.JWT_REFRESH_EXPIRES_IN = '7d';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const jwt = require('jsonwebtoken');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, RefreshToken } = require('../models');
const authService = require('../services/authService');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { hashPassword } = require('../utils/password');
const { hashSecureToken } = require('../utils/tokenHash');
const { toSafeUser } = require('../utils/userSerializer');
const { USER_ROLES } = require('../config/constants');
const { AppError } = require('../utils/errors');
const { getAccessTokenSecret } = require('../config/jwt');
const { createTestRun } = require('./helpers/testIsolation');

const TEST_PASSWORD = 'SecurePass1';
const run = createTestRun();
const emails = {
  admin: run.email('auth-admin'),
  staff: run.email('auth-staff'),
  inactive: run.email('auth-inactive'),
};

let activeUser;
let inactiveUser;
let staffUser;

function createMockRes() {
  const res = {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
  return res;
}

async function runMiddleware(middleware, req) {
  let caughtError = null;
  let nextCalled = false;

  await middleware(req, createMockRes(), (err) => {
    nextCalled = true;
    caughtError = err || null;
  });

  return { error: caughtError, nextCalled };
}

before(async () => {
  await connectDatabase();

  const passwordHash = await hashPassword(TEST_PASSWORD);

  activeUser = await User.create({
    name: 'Active Admin',
    email: emails.admin,
    passwordHash,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  staffUser = await User.create({
    name: 'Active Staff',
    email: emails.staff,
    passwordHash,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  inactiveUser = await User.create({
    name: 'Inactive User',
    email: emails.inactive,
    passwordHash,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: false,
    isEmailVerified: true,
  });
});

after(async () => {
  const testUserIds = [activeUser, staffUser, inactiveUser]
    .filter(Boolean)
    .map((user) => user._id);

  if (testUserIds.length > 0) {
    await RefreshToken.deleteMany({ user: { $in: testUserIds } });
  }
  await User.deleteMany(run.emailFilter());
  await disconnectDatabase();
});

describe('Email/password login', () => {
  it('logs in with valid email/password', async () => {
    const result = await authService.login(emails.admin, TEST_PASSWORD);

    assert.ok(result.accessToken);
    assert.ok(result.refreshToken);
    assert.equal(result.user.email, emails.admin);
    assert.equal(result.user.passwordHash, undefined);
  });

  it('rejects invalid password with generic error', async () => {
    await assert.rejects(
      () => authService.login(emails.admin, 'WrongPass1'),
      (err) =>
        err.statusCode === 401 && err.message === authService.INVALID_CREDENTIALS_MESSAGE
    );
  });

  it('rejects nonexistent email with generic error', async () => {
    await assert.rejects(
      () => authService.login(run.email('missing'), TEST_PASSWORD),
      (err) =>
        err.statusCode === 401 && err.message === authService.INVALID_CREDENTIALS_MESSAGE
    );
  });

  it('rejects inactive user with generic error', async () => {
    await assert.rejects(
      () => authService.login(emails.inactive, TEST_PASSWORD),
      (err) =>
        err.statusCode === 401 && err.message === authService.INVALID_CREDENTIALS_MESSAGE
    );
  });

  it('rejects missing password via validator', async () => {
    const { validateLoginBody } = require('../validators/authValidator');
    const result = validateLoginBody({ email: emails.admin });
    assert.equal(result.valid, false);
  });
});

describe('Access JWT', () => {
  it('creates a JWT with sub and role', async () => {
    const token = authService.createAccessToken(activeUser);
    const decoded = jwt.verify(token, getAccessTokenSecret());

    assert.equal(decoded.sub, activeUser._id.toString());
    assert.equal(decoded.role, USER_ROLES.ADMIN);
    assert.equal(decoded.password, undefined);
  });

  it('requireAuth rejects missing token', async () => {
    const { error } = await runMiddleware(requireAuth, { headers: {} });
    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 401);
  });

  it('requireAuth accepts valid token', async () => {
    const token = authService.createAccessToken(activeUser);
    const { error, nextCalled } = await runMiddleware(requireAuth, {
      headers: { authorization: `Bearer ${token}` },
    });

    assert.equal(error, null);
    assert.equal(nextCalled, true);
  });

  it('requireAuth rejects expired/invalid token', async () => {
    const badToken = jwt.sign({ sub: activeUser._id.toString(), role: USER_ROLES.ADMIN }, 'wrong');
    const { error } = await runMiddleware(requireAuth, {
      headers: { authorization: `Bearer ${badToken}` },
    });

    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 401);
  });
});

describe('Role middleware', () => {
  it('allows ADMIN on admin-only route', async () => {
    const middleware = requireRole(USER_ROLES.ADMIN);
    const { error, nextCalled } = await runMiddleware(middleware, {
      user: { role: USER_ROLES.ADMIN },
    });

    assert.equal(error, null);
    assert.equal(nextCalled, true);
  });

  it('rejects FUNDRAISING_STAFF on admin-only route', async () => {
    const middleware = requireRole(USER_ROLES.ADMIN);
    const { error } = await runMiddleware(middleware, {
      user: { role: USER_ROLES.FUNDRAISING_STAFF },
    });

    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 403);
  });
});

describe('Refresh token lifecycle', () => {
  it('refreshes with valid cookie token and rotates', async () => {
    const login = await authService.login(emails.staff, TEST_PASSWORD);
    const firstRefresh = await authService.refreshSession(login.refreshToken);

    assert.ok(firstRefresh.accessToken);
    assert.ok(firstRefresh.refreshToken);
    assert.notEqual(firstRefresh.refreshToken, login.refreshToken);

    const oldRecord = await RefreshToken.findOne({ tokenHash: hashSecureToken(login.refreshToken) });
    assert.ok(oldRecord.revokedAt);
  });

  it('rejects expired refresh token', async () => {
    const rawToken = `expired-refresh-token-${run.id}`;
    await RefreshToken.create({
      user: staffUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() - 1000),
    });

    await assert.rejects(
      () => authService.refreshSession(rawToken),
      (err) => err.statusCode === 401
    );
  });

  it('rejects revoked refresh token', async () => {
    const rawToken = `revoked-refresh-token-${run.id}`;
    await RefreshToken.create({
      user: staffUser._id,
      tokenHash: hashSecureToken(rawToken),
      expiresAt: new Date(Date.now() + 60_000),
      revokedAt: new Date(),
    });

    await assert.rejects(
      () => authService.refreshSession(rawToken),
      (err) => err.statusCode === 401
    );
  });

  it('logout revokes refresh token', async () => {
    const login = await authService.login(emails.staff, TEST_PASSWORD);
    await authService.logout(login.refreshToken);

    const record = await RefreshToken.findOne({ tokenHash: hashSecureToken(login.refreshToken) });
    assert.ok(record.revokedAt);

    await assert.rejects(
      () => authService.refreshSession(login.refreshToken),
      (err) => err.statusCode === 401
    );
  });

  it('logout succeeds without cookie token', async () => {
    await authService.logout(undefined);
  });
});

describe('Current user', () => {
  it('/me returns safe user data without passwordHash', async () => {
    const user = await authService.getCurrentUser(activeUser._id.toString());
    const serialized = JSON.stringify(user);

    assert.equal(user.email, emails.admin);
    assert.equal(user.passwordHash, undefined);
    assert.equal(serialized.includes('passwordHash'), false);
  });
});

describe('Response safety', () => {
  it('never includes refresh token in login service payload fields exposed to controller', async () => {
    const result = await authService.login(emails.admin, TEST_PASSWORD);
    const safeUser = toSafeUser(result.user);

    assert.equal(safeUser.passwordHash, undefined);
    assert.equal(result.user.refreshToken, undefined);
    assert.ok(result.refreshToken);
  });
});
