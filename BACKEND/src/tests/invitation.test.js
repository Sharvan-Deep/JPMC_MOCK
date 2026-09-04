/**
 * Focused invitation module tests using Node's built-in test runner.
 *
 * Requires a running MongoDB instance (MONGODB_URI).
 * Mocks outbound email so no SMTP credentials are needed.
 *
 * Uses unique per-run emails and deletes only those records.
 */
require('dotenv').config();

process.env.FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
process.env.INVITATION_RESEND_COOLDOWN_MINUTES = '0';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Invitation } = require('../models');
const invitationService = require('../services/invitationService');
const { hashInvitationToken } = require('../utils/tokenHash');
const { INVITATION_STATUSES, USER_ROLES } = require('../config/constants');
const { parseInvitationCsvBuffer } = require('../validators/invitationValidator');
const { createTestRun } = require('./helpers/testIsolation');

const run = createTestRun();
const emails = {
  admin: run.email('invite-admin'),
  invitee: run.email('invitee1'),
  duplicate: run.email('duplicate-pending'),
  verify: run.email('verify'),
  expired: run.email('expired'),
  revoked: run.email('revoked'),
  activate: run.email('activate'),
  reuse: run.email('reuse'),
  existing: run.email('existing'),
  csv1: run.email('csv1'),
  csv2: run.email('csv2'),
  resend: run.email('resend'),
};

let adminUser;
let originalSendEmail;

before(async () => {
  await connectDatabase();

  adminUser = await User.create({
    name: 'Test Admin',
    email: emails.admin,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  const mailService = require('../services/mailService');
  originalSendEmail = mailService.sendEmail;
  mailService.sendEmail = async () => ({ success: true, messageId: 'test-id' });
});

after(async () => {
  const mailService = require('../services/mailService');
  mailService.sendEmail = originalSendEmail;

  const ownedByTestAdmin = adminUser?._id
    ? [{ invitedBy: adminUser._id }]
    : [];

  await Invitation.deleteMany({
    $or: [run.emailFilter(), ...ownedByTestAdmin],
  });
  await User.deleteMany(run.emailFilter());
  await disconnectDatabase();
});

describe('Admin Invitation + Account Activation', () => {
  it('creates an admin invitation and sends email', async () => {
    const invitation = await invitationService.createInvitation({
      name: 'Invitee One',
      email: emails.invitee,
      invitedBy: adminUser._id,
    });

    assert.equal(invitation.email, emails.invitee);
    assert.equal(invitation.status, INVITATION_STATUSES.PENDING);
    assert.equal(invitation.tokenHash, undefined);
  });

  it('rejects duplicate pending invitation', async () => {
    await Invitation.create({
      name: 'Pending Duplicate',
      email: emails.duplicate,
      tokenHash: hashInvitationToken(`duplicate-token-${run.id}`),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      status: INVITATION_STATUSES.PENDING,
      invitedBy: adminUser._id,
    });

    await assert.rejects(
      () =>
        invitationService.createInvitation({
          name: 'Pending Duplicate',
          email: emails.duplicate,
          invitedBy: adminUser._id,
        }),
      (err) => err.statusCode === 409
    );
  });

  it('rejects invalid email', async () => {
    const { validateCreateInvitationBody } = require('../validators/invitationValidator');
    const result = validateCreateInvitationBody({ name: 'Bad', email: 'not-an-email' });
    assert.equal(result.valid, false);
  });

  it('verifies a valid invitation token', async () => {
    const rawToken = `verify-${run.id}`;
    await Invitation.create({
      name: 'Verify User',
      email: emails.verify,
      tokenHash: hashInvitationToken(rawToken),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      status: INVITATION_STATUSES.PENDING,
      invitedBy: adminUser._id,
    });

    const result = await invitationService.verifyInvitationToken(rawToken);
    assert.equal(result.valid, true);
    assert.equal(result.email, emails.verify);
  });

  it('rejects expired token', async () => {
    const rawToken = `expired-${run.id}`;
    await Invitation.create({
      name: 'Expired User',
      email: emails.expired,
      tokenHash: hashInvitationToken(rawToken),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() - 60 * 1000),
      status: INVITATION_STATUSES.PENDING,
      invitedBy: adminUser._id,
    });

    const result = await invitationService.verifyInvitationToken(rawToken);
    assert.equal(result.valid, false);
  });

  it('rejects revoked invitation', async () => {
    const rawToken = `revoked-${run.id}`;
    await Invitation.create({
      name: 'Revoked User',
      email: emails.revoked,
      tokenHash: hashInvitationToken(rawToken),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      status: INVITATION_STATUSES.REVOKED,
      invitedBy: adminUser._id,
    });

    const result = await invitationService.verifyInvitationToken(rawToken);
    assert.equal(result.valid, false);
  });

  it('activates account successfully', async () => {
    const rawToken = `activate-${run.id}`;
    await Invitation.create({
      name: 'Activate User',
      email: emails.activate,
      tokenHash: hashInvitationToken(rawToken),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      status: INVITATION_STATUSES.PENDING,
      invitedBy: adminUser._id,
    });

    const result = await invitationService.activateAccount({
      token: rawToken,
      password: 'SecurePass1',
    });

    assert.equal(result.user.email, emails.activate);
    assert.equal(result.user.isActive, true);
    assert.equal(result.user.isEmailVerified, true);

    const storedUser = await User.findOne({ email: emails.activate }).select('+passwordHash');
    assert.ok(storedUser.passwordHash);
    assert.notEqual(storedUser.passwordHash, 'SecurePass1');
  });

  it('prevents token reuse after activation', async () => {
    const rawToken = `reuse-${run.id}`;
    await Invitation.create({
      name: 'Reuse User',
      email: emails.reuse,
      tokenHash: hashInvitationToken(rawToken),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      status: INVITATION_STATUSES.ACCEPTED,
      invitedBy: adminUser._id,
      acceptedAt: new Date(),
    });

    await assert.rejects(
      () =>
        invitationService.activateAccount({
          token: rawToken,
          password: 'SecurePass1',
        }),
      (err) => err.statusCode === 400
    );
  });

  it('prevents duplicate user on activation', async () => {
    await User.create({
      name: 'Existing User',
      email: emails.existing,
      role: USER_ROLES.FUNDRAISING_STAFF,
      isActive: true,
    });

    const rawToken = `existing-${run.id}`;
    await Invitation.create({
      name: 'Existing User',
      email: emails.existing,
      tokenHash: hashInvitationToken(rawToken),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000),
      status: INVITATION_STATUSES.PENDING,
      invitedBy: adminUser._id,
    });

    await assert.rejects(
      () =>
        invitationService.activateAccount({
          token: rawToken,
          password: 'SecurePass1',
        }),
      (err) => err.statusCode === 409
    );
  });

  it('imports invitations from CSV', async () => {
    const csv = [
      'name,email',
      `CSV User 1,${emails.csv1}`,
      `CSV User 2,${emails.csv2}`,
      `CSV User 1,${emails.csv1}`,
    ].join('\n');

    const summary = await invitationService.importInvitationsFromCsv(
      Buffer.from(csv, 'utf8'),
      adminUser._id
    );

    assert.equal(summary.totalRows, 3);
    assert.equal(summary.invited, 2);
    assert.equal(summary.skipped, 1);
    assert.ok(summary.errors.some((e) => e.message.includes('Duplicate email')));
  });

  it('resend creates a new token hash', async () => {
    const invitation = await Invitation.create({
      name: 'Resend User',
      email: emails.resend,
      tokenHash: hashInvitationToken(`old-token-${run.id}`),
      role: USER_ROLES.FUNDRAISING_STAFF,
      expiresAt: new Date(Date.now() - 60 * 1000),
      status: INVITATION_STATUSES.EXPIRED,
      invitedBy: adminUser._id,
    });

    const beforeHash = invitation.tokenHash;
    const updated = await invitationService.resendInvitation(invitation._id.toString());

    assert.notEqual(updated.tokenHash, beforeHash);
    assert.equal(updated.status, INVITATION_STATUSES.PENDING);
  });
});

describe('CSV parser', () => {
  it('parses invitation CSV headers', () => {
    const { rows, headers } = parseInvitationCsvBuffer(
      Buffer.from('name,email\nAlice,alice@example.com', 'utf8')
    );
    assert.deepEqual(headers, ['name', 'email']);
    assert.equal(rows[0].email, 'alice@example.com');
  });
});
