/**
 * Lead Management module tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-lead-module';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company, Lead, LeadNote, LeadActivity } = require('../models');
const leadService = require('../services/leadService');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const authService = require('../services/authService');
const { AppError } = require('../utils/errors');
const {
  USER_ROLES,
  LEAD_STATUSES,
  LEAD_PRIORITIES,
  LEAD_ACTIVITY_TYPES,
} = require('../config/constants');
const {
  validateCreateLeadBody,
  validateUpdateLeadBody,
  validateListLeadsQuery,
} = require('../validators/leadValidator');
const { createTestRun } = require('./helpers/testIsolation');

const run = createTestRun();
const emails = {
  admin: run.email('lead-admin'),
  staff: run.email('lead-staff'),
  otherStaff: run.email('lead-other-staff'),
  inactive: run.email('lead-inactive'),
};

let adminUser;
let staffUser;
let otherStaffUser;
let inactiveUser;
let company;
let otherCompany;
let createdLeadId;

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

  adminUser = await User.create({
    name: 'Lead Admin',
    email: emails.admin,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  staffUser = await User.create({
    name: 'Lead Staff',
    email: emails.staff,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  otherStaffUser = await User.create({
    name: 'Other Staff',
    email: emails.otherStaff,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  inactiveUser = await User.create({
    name: 'Inactive Staff',
    email: emails.inactive,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: false,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `Lead Test Company ${run.id}`,
    companyNameKey: `lead-test-company-${run.id}`,
  });

  otherCompany = await Company.create({
    company_name: `Lead Other Company ${run.id}`,
    companyNameKey: `lead-other-company-${run.id}`,
  });
});

after(async () => {
  const testUserIds = [adminUser, staffUser, otherStaffUser, inactiveUser]
    .filter(Boolean)
    .map((user) => user._id);

  const leads = await Lead.find({
    $or: [{ company: company?._id }, { company: otherCompany?._id }],
  }).select('_id');
  const leadIds = leads.map((lead) => lead._id);

  if (leadIds.length > 0) {
    await LeadNote.deleteMany({ lead: { $in: leadIds } });
    await LeadActivity.deleteMany({ lead: { $in: leadIds } });
    await Lead.deleteMany({ _id: { $in: leadIds } });
  }

  if (company?._id) {
    await Company.deleteMany({ _id: { $in: [company._id, otherCompany._id] } });
  }

  if (testUserIds.length > 0) {
    await User.deleteMany({ _id: { $in: testUserIds } });
  }

  await disconnectDatabase();
});

describe('Lead Management', () => {
  it('creates a lead for an existing company', async () => {
    const result = await leadService.createLead(
      { companyId: company._id.toString(), priority: LEAD_PRIORITIES.HIGH },
      adminUser
    );

    createdLeadId = result.lead.id.toString();
    assert.equal(result.lead.status, LEAD_STATUSES.NEW);
    assert.equal(result.lead.priority, LEAD_PRIORITIES.HIGH);
    assert.equal(result.lead.company.company_name, company.company_name);
    assert.equal(result.lead.createdBy.email, emails.admin);
    assert.equal(result.lead.assignedTo.email, emails.admin);
  });

  it('rejects lead creation for invalid company', async () => {
    await assert.rejects(
      () =>
        leadService.createLead(
          { companyId: '507f1f77bcf86cd799439011' },
          adminUser
        ),
      (err) => err.statusCode === 404 && err.code === 'COMPANY_NOT_FOUND'
    );
  });

  it('rejects duplicate active lead for the same company', async () => {
    await assert.rejects(
      () =>
        leadService.createLead({ companyId: company._id.toString() }, staffUser),
      (err) => err.statusCode === 409 && err.code === 'ACTIVE_LEAD_EXISTS'
    );
  });

  it('lists leads with pagination', async () => {
    const result = await leadService.listLeads({ page: 1, limit: 20 });

    assert.ok(Array.isArray(result.leads));
    assert.ok(result.leads.length >= 1);
    assert.equal(result.pagination.page, 1);
    assert.equal(result.pagination.limit, 20);
    assert.ok(result.pagination.total >= 1);
  });

  it('filters leads by status', async () => {
    const result = await leadService.listLeads({ status: LEAD_STATUSES.NEW });

    assert.ok(result.leads.every((lead) => lead.status === LEAD_STATUSES.NEW));
  });

  it('filters leads by priority', async () => {
    const result = await leadService.listLeads({ priority: LEAD_PRIORITIES.HIGH });

    assert.ok(result.leads.every((lead) => lead.priority === LEAD_PRIORITIES.HIGH));
  });

  it('returns lead detail with notes and activities arrays', async () => {
    const result = await leadService.getLeadById(createdLeadId);

    assert.equal(result.lead.id.toString(), createdLeadId);
    assert.ok(result.lead.company);
    assert.ok(result.lead.assignedTo);
    assert.ok(Array.isArray(result.notes));
    assert.ok(Array.isArray(result.activities));
  });

  it('updates lead status and records activity', async () => {
    const result = await leadService.updateLead(
      createdLeadId,
      { status: LEAD_STATUSES.CONTACTED },
      adminUser
    );

    assert.equal(result.lead.status, LEAD_STATUSES.CONTACTED);
    assert.ok(
      result.activities.some(
        (activity) =>
          activity.activityType === LEAD_ACTIVITY_TYPES.STATUS_CHANGED &&
          activity.description.includes('CONTACTED')
      )
    );
  });

  it('rejects invalid status updates', async () => {
    const validation = validateUpdateLeadBody({ status: 'INVALID' });
    assert.equal(validation.valid, false);
  });

  it('assigns lead to active staff and records activity', async () => {
    const result = await leadService.assignLead(
      createdLeadId,
      staffUser._id.toString(),
      adminUser
    );

    assert.equal(result.lead.assignedTo.email, emails.staff);
    assert.ok(
      result.activities.some((activity) => activity.description.includes(emails.staff))
    );
  });

  it('rejects assignment to inactive user', async () => {
    await assert.rejects(
      () =>
        leadService.assignLead(
          createdLeadId,
          inactiveUser._id.toString(),
          adminUser
        ),
      (err) => err.statusCode === 400 && err.code === 'USER_INACTIVE'
    );
  });

  it('allows assigned staff to add notes', async () => {
    const note = await leadService.addNote(
      createdLeadId,
      'Discussed Water for Schools proposal.',
      staffUser
    );

    assert.equal(note.note, 'Discussed Water for Schools proposal.');
    assert.equal(note.user.email, emails.staff);
  });

  it('lists notes chronologically', async () => {
    await leadService.addNote(createdLeadId, 'Second note', staffUser);
    const notes = await leadService.listNotes(createdLeadId);

    assert.ok(notes.length >= 2);
    assert.ok(notes[0].createdAt <= notes[1].createdAt);
  });

  it('allows assigned staff to add activities', async () => {
    const activity = await leadService.addActivity(
      createdLeadId,
      {
        activityType: LEAD_ACTIVITY_TYPES.CALL,
        description: 'Discussed CSR funding opportunity.',
      },
      staffUser
    );

    assert.equal(activity.activityType, LEAD_ACTIVITY_TYPES.CALL);
    assert.equal(activity.description, 'Discussed CSR funding opportunity.');
  });

  it('lists activities chronologically', async () => {
    const activities = await leadService.listActivities(createdLeadId);

    assert.ok(activities.length >= 1);
    for (let i = 1; i < activities.length; i += 1) {
      assert.ok(activities[i - 1].createdAt <= activities[i].createdAt);
    }
  });

  it('rejects updates from staff without access', async () => {
    await assert.rejects(
      () =>
        leadService.updateLead(
          createdLeadId,
          { priority: LEAD_PRIORITIES.LOW },
          otherStaffUser
        ),
      (err) => err.statusCode === 403
    );
  });

  it('rejects staff-only assignment endpoint', async () => {
    await assert.rejects(
      () =>
        leadService.assignLead(
          createdLeadId,
          otherStaffUser._id.toString(),
          staffUser
        ),
      (err) => err.statusCode === 403
    );
  });

  it('archives active lead instead of deleting it', async () => {
    const archived = await leadService.archiveLead(createdLeadId, adminUser);

    assert.equal(archived.lead.status, LEAD_STATUSES.LOST);

    const stored = await Lead.findById(createdLeadId);
    assert.ok(stored);
    assert.equal(stored.status, LEAD_STATUSES.LOST);
  });

  it('allows creating a new lead after previous lead is closed', async () => {
    const result = await leadService.createLead(
      { companyId: company._id.toString() },
      staffUser
    );

    assert.equal(result.lead.status, LEAD_STATUSES.NEW);
    assert.equal(result.lead.assignedTo.email, emails.staff);
  });

  it('validates create lead body', async () => {
    const invalid = validateCreateLeadBody({ companyId: 'bad-id' });
    assert.equal(invalid.valid, false);

    const valid = validateCreateLeadBody({
      companyId: company._id.toString(),
      priority: LEAD_PRIORITIES.MEDIUM,
    });
    assert.equal(valid.valid, true);
  });

  it('validates list query filters', async () => {
    const invalid = validateListLeadsQuery({ status: 'BAD' });
    assert.equal(invalid.valid, false);

    const valid = validateListLeadsQuery({
      status: LEAD_STATUSES.NEW,
      priority: LEAD_PRIORITIES.MEDIUM,
      page: 1,
      limit: 10,
    });
    assert.equal(valid.valid, true);
  });
});

describe('Lead route authentication', () => {
  it('requireAuth rejects missing token', async () => {
    const { error } = await runMiddleware(requireAuth, { headers: {} });
    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 401);
  });

  it('requireAuth accepts valid token', async () => {
    const token = authService.createAccessToken(adminUser);
    const { error, nextCalled } = await runMiddleware(requireAuth, {
      headers: { authorization: `Bearer ${token}` },
    });

    assert.equal(error, null);
    assert.equal(nextCalled, true);
  });

  it('requireRole allows fundraising staff', async () => {
    const middleware = requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF);
    const { error, nextCalled } = await runMiddleware(middleware, {
      user: { role: USER_ROLES.FUNDRAISING_STAFF },
    });

    assert.equal(error, null);
    assert.equal(nextCalled, true);
  });
});
