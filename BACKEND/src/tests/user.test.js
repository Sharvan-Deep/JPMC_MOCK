/**
 * User Management module tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-user-module';
process.env.JWT_ACCESS_EXPIRES_IN = '15m';
process.env.JWT_REFRESH_EXPIRES_IN = '7d';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, RefreshToken } = require('../models');
const userService = require('../services/userService');
const authService = require('../services/authService');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const { hashPassword } = require('../utils/password');
const { hashSecureToken } = require('../utils/tokenHash');
const { toSafeUser } = require('../utils/userSerializer');
const { USER_ROLES } = require('../config/constants');
const { AppError } = require('../utils/errors');
const {
  validateListUsersQuery,
  validateUpdateUserBody,
  validateRoleBody,
  validateStatusBody,
} = require('../validators/userValidator');
const { createTestRun } = require('./helpers/testIsolation');

const TEST_PASSWORD = 'SecurePass1';
const run = createTestRun();
const emails = {
  admin: run.email('user-admin'),
  adminBackup: run.email('user-admin-backup'),
  staff: run.email('user-staff'),
  searchable: run.email('user-searchable'),
};

let adminUser;
let backupAdminUser;
let staffUser;
let searchableUser;

function createMockRes() {
  return {
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

  adminUser = await User.create({
    name: 'Primary Admin',
    email: emails.admin,
    passwordHash,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  backupAdminUser = await User.create({
    name: 'Backup Admin',
    email: emails.adminBackup,
    passwordHash,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  staffUser = await User.create({
    name: 'Fundraising Staff',
    email: emails.staff,
    passwordHash,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  searchableUser = await User.create({
    name: 'Sharvan Searchable',
    email: emails.searchable,
    passwordHash,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: false,
    isEmailVerified: true,
  });
});

after(async () => {
  const testUsers = [adminUser, backupAdminUser, staffUser, searchableUser]
    .filter(Boolean)
    .map((user) => user._id);

  if (testUsers.length > 0) {
    await RefreshToken.deleteMany({ user: { $in: testUsers } });
    await User.deleteMany({ _id: { $in: testUsers } });
  }

  await disconnectDatabase();
});

describe('User Management', () => {
  it('lists users with pagination', async () => {
    const result = await userService.listUsers({ page: 1, limit: 2 });

    assert.equal(result.users.length, 2);
    assert.ok(result.pagination.total >= 4);
    assert.equal(result.users[0].passwordHash, undefined);
  });

  it('searches users by name or email', async () => {
    const result = await userService.listUsers({ search: 'Sharvan' });

    assert.ok(result.users.some((user) => user.email === emails.searchable));
  });

  it('filters users by role and active status', async () => {
    const roleResult = await userService.listUsers({ role: USER_ROLES.FUNDRAISING_STAFF });
    const inactiveResult = await userService.listUsers({ isActive: false });

    assert.ok(roleResult.users.every((user) => user.role === USER_ROLES.FUNDRAISING_STAFF));
    assert.ok(inactiveResult.users.every((user) => user.isActive === false));
  });

  it('returns a single safe user', async () => {
    const user = await userService.getUserById(staffUser._id.toString());

    assert.equal(user.email, emails.staff);
    assert.equal(user.passwordHash, undefined);
  });

  it('updates only the user name', async () => {
    const updated = await userService.updateUserProfile(staffUser._id.toString(), {
      name: 'Updated Staff Name',
    });

    assert.equal(updated.name, 'Updated Staff Name');
    assert.equal(updated.email, emails.staff);
  });

  it('rejects protected field updates through profile PATCH validation', async () => {
    const validation = validateUpdateUserBody({
      name: 'Valid Name',
      role: USER_ROLES.ADMIN,
      isActive: false,
    });

    assert.equal(validation.valid, false);
  });

  it('allows admin to change another user role', async () => {
    const updated = await userService.updateUserRole(
      staffUser._id.toString(),
      USER_ROLES.ADMIN,
      adminUser._id.toString()
    );

    assert.equal(updated.role, USER_ROLES.ADMIN);

    await userService.updateUserRole(
      staffUser._id.toString(),
      USER_ROLES.FUNDRAISING_STAFF,
      adminUser._id.toString()
    );
  });

  it('rejects invalid role values', async () => {
    const validation = validateRoleBody({ role: 'SUPERADMIN' });
    assert.equal(validation.valid, false);
  });

  it('prevents admin self-demotion', async () => {
    await assert.rejects(
      () =>
        userService.updateUserRole(
          adminUser._id.toString(),
          USER_ROLES.FUNDRAISING_STAFF,
          adminUser._id.toString()
        ),
      (err) => err.statusCode === 400 && err.code === 'SELF_DEMOTION_FORBIDDEN'
    );
  });

  it('allows admin to deactivate another user', async () => {
    const updated = await userService.updateUserStatus(
      searchableUser._id.toString(),
      false,
      adminUser._id.toString()
    );

    assert.equal(updated.isActive, false);
  });

  it('prevents admin self-deactivation', async () => {
    await assert.rejects(
      () =>
        userService.updateUserStatus(
          adminUser._id.toString(),
          false,
          adminUser._id.toString()
        ),
      (err) => err.statusCode === 400 && err.code === 'SELF_MODIFICATION_FORBIDDEN'
    );
  });

  it('prevents deactivated users from logging in', async () => {
    await userService.updateUserStatus(
      staffUser._id.toString(),
      false,
      adminUser._id.toString()
    );

    await assert.rejects(
      () => authService.login(emails.staff, TEST_PASSWORD),
      (err) =>
        err.statusCode === 401 &&
        err.message === authService.INVALID_CREDENTIALS_MESSAGE
    );

    await userService.updateUserStatus(
      staffUser._id.toString(),
      true,
      adminUser._id.toString()
    );
  });

  it('rejects refresh for inactive users', async () => {
    const login = await authService.login(emails.staff, TEST_PASSWORD);
    await userService.updateUserStatus(
      staffUser._id.toString(),
      false,
      adminUser._id.toString()
    );

    await assert.rejects(
      () => authService.refreshSession(login.refreshToken),
      (err) => err.statusCode === 401
    );

    await userService.updateUserStatus(
      staffUser._id.toString(),
      true,
      adminUser._id.toString()
    );
  });

  it('never exposes passwordHash in serialized users', async () => {
    const stored = await User.findById(staffUser._id).select('+passwordHash');
    const safe = toSafeUser(stored);

    assert.ok(stored.passwordHash);
    assert.equal(safe.passwordHash, undefined);
    assert.equal(JSON.stringify(safe).includes('passwordHash'), false);
  });

  it('validates list query inputs', async () => {
    const invalid = validateListUsersQuery({ role: 'BAD' });
    assert.equal(invalid.valid, false);

    const valid = validateListUsersQuery({
      page: 1,
      limit: 10,
      search: 'admin',
      role: USER_ROLES.ADMIN,
      isActive: 'true',
    });
    assert.equal(valid.valid, true);
  });

  it('validates status body', async () => {
    const invalid = validateStatusBody({ isActive: 'no' });
    assert.equal(invalid.valid, false);

    const valid = validateStatusBody({ isActive: false });
    assert.equal(valid.valid, true);
  });
});

describe('User route authorization', () => {
  it('requireAuth rejects missing token', async () => {
    const { error } = await runMiddleware(requireAuth, { headers: {} });
    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 401);
  });

  it('requireRole rejects fundraising staff from admin routes', async () => {
    const middleware = requireRole(USER_ROLES.ADMIN);
    const { error } = await runMiddleware(middleware, {
      user: { role: USER_ROLES.FUNDRAISING_STAFF },
    });

    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 403);
  });

  it('requireRole allows admin access', async () => {
    const middleware = requireRole(USER_ROLES.ADMIN);
    const { error, nextCalled } = await runMiddleware(middleware, {
      user: { role: USER_ROLES.ADMIN },
    });

    assert.equal(error, null);
    assert.equal(nextCalled, true);
  });
});
