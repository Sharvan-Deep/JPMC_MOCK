/**
 * Dashboard API tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-dashboard-module';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company, Lead, LeadActivity } = require('../models');
const dashboardService = require('../services/dashboardService');
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
const { validatePaginationQuery } = require('../validators/dashboardValidator');
const { createTestRun } = require('./helpers/testIsolation');

const run = createTestRun();
const emails = {
  admin: run.email('dash-admin'),
  staff: run.email('dash-staff'),
};

let adminUser;
let staffUser;
let washCompany;
let noWashCompany;
let followUpCompany;
let highLead;
let mediumLead;
let followUpLead;
let wonLead;

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
    name: 'Dashboard Admin',
    email: emails.admin,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  staffUser = await User.create({
    name: 'Dashboard Staff',
    email: emails.staff,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  washCompany = await Company.create({
    company_name: `Dashboard WASH Co ${run.id}`,
    companyNameKey: `dashboard-wash-co-${run.id}`,
    wash_record_count: 4,
    total_wash_spend_crore: 2.5,
    total_water_spend_crore: 1.5,
    total_sanitation_spend_crore: 1.0,
  });

  noWashCompany = await Company.create({
    company_name: `Dashboard Plain Co ${run.id}`,
    companyNameKey: `dashboard-plain-co-${run.id}`,
  });

  followUpCompany = await Company.create({
    company_name: `Dashboard Follow Up Co ${run.id}`,
    companyNameKey: `dashboard-followup-co-${run.id}`,
  });

  highLead = await Lead.create({
    company: washCompany._id,
    assignedTo: staffUser._id,
    createdBy: adminUser._id,
    status: LEAD_STATUSES.CONTACTED,
    priority: LEAD_PRIORITIES.HIGH,
  });

  mediumLead = await Lead.create({
    company: noWashCompany._id,
    assignedTo: adminUser._id,
    createdBy: adminUser._id,
    status: LEAD_STATUSES.NEW,
    priority: LEAD_PRIORITIES.MEDIUM,
  });

  followUpLead = await Lead.create({
    company: followUpCompany._id,
    assignedTo: staffUser._id,
    createdBy: adminUser._id,
    status: LEAD_STATUSES.FOLLOW_UP,
    priority: LEAD_PRIORITIES.LOW,
  });

  wonLead = await Lead.create({
    company: noWashCompany._id,
    assignedTo: adminUser._id,
    createdBy: adminUser._id,
    status: LEAD_STATUSES.WON,
    priority: LEAD_PRIORITIES.MEDIUM,
  });

  await LeadActivity.create({
    lead: highLead._id,
    user: staffUser._id,
    activityType: LEAD_ACTIVITY_TYPES.CALL,
    description: 'Initial outreach call',
  });

  await LeadActivity.create({
    lead: followUpLead._id,
    user: staffUser._id,
    activityType: LEAD_ACTIVITY_TYPES.FOLLOW_UP,
    description: 'Awaiting callback',
  });
});

after(async () => {
  const companyIds = [washCompany?._id, noWashCompany?._id, followUpCompany?._id].filter(Boolean);
  const leads = await Lead.find({ company: { $in: companyIds } }).select('_id');
  const leadIds = leads.map((lead) => lead._id);

  if (leadIds.length > 0) {
    await LeadActivity.deleteMany({ lead: { $in: leadIds } });
    await Lead.deleteMany({ _id: { $in: leadIds } });
  }

  if (companyIds.length > 0) {
    await Company.deleteMany({ _id: { $in: companyIds } });
  }

  await User.deleteMany(run.emailFilter());
  await disconnectDatabase();
});

describe('Dashboard APIs', () => {
  it('returns dashboard summary metrics from MongoDB', async () => {
    const summary = await dashboardService.getDashboardSummary();

    assert.ok(summary.companies.total >= 3);
    assert.ok(summary.wash.companiesWithWASH >= 1);
    assert.ok(summary.wash.totalWASHSpend >= 2.5);
    assert.ok(summary.wash.totalWaterSpend >= 1.5);
    assert.ok(summary.wash.totalSanitationSpend >= 1.0);
    assert.ok(summary.leads.total >= 4);
    assert.ok(summary.leads.active >= 3);
    assert.ok(summary.leads.won >= 1);
    assert.equal(summary.leads.byStatus[LEAD_STATUSES.WON], 1);
    assert.ok(summary.activities.recentCount >= 2);
    assert.ok(summary.activities.byType[LEAD_ACTIVITY_TYPES.CALL] >= 1);
  });

  it('includes lead status distribution for all enum values', async () => {
    const summary = await dashboardService.getDashboardSummary();

    for (const status of Object.values(LEAD_STATUSES)) {
      assert.equal(typeof summary.leads.byStatus[status], 'number');
    }
  });

  it('returns top prospects sorted by priority then recency', async () => {
    const result = await dashboardService.getTopProspects({ page: 1, limit: 10 });

    assert.ok(result.prospects.length >= 3);
    assert.equal(result.prospects[0].priority, LEAD_PRIORITIES.HIGH);
    assert.ok(result.pagination.total >= 3);
  });

  it('paginates top prospects', async () => {
    const page1 = await dashboardService.getTopProspects({ page: 1, limit: 1 });
    const page2 = await dashboardService.getTopProspects({ page: 2, limit: 1 });

    assert.equal(page1.prospects.length, 1);
    assert.equal(page2.prospects.length, 1);
    assert.notEqual(page1.prospects[0].id.toString(), page2.prospects[0].id.toString());
  });

  it('returns recent leads with safe user fields', async () => {
    const result = await dashboardService.getRecentLeads({ page: 1, limit: 10 });

    assert.ok(result.leads.length >= 4);
    assert.ok(result.leads[0].company.company_name);
    assert.equal(result.leads[0].assignedTo.passwordHash, undefined);
    assert.ok(result.leads[0].updatedAt);
  });

  it('paginates recent leads', async () => {
    const result = await dashboardService.getRecentLeads({ page: 1, limit: 2 });

    assert.equal(result.leads.length, 2);
    assert.equal(result.pagination.limit, 2);
    assert.ok(result.pagination.total >= 4);
  });

  it('returns follow-up leads in FOLLOW_UP status oldest first', async () => {
    const result = await dashboardService.getFollowUps({ page: 1, limit: 10 });

    assert.ok(result.followUps.length >= 1);
    assert.ok(result.followUps.every((lead) => lead.status === LEAD_STATUSES.FOLLOW_UP));
    assert.equal(result.followUps[0].id.toString(), followUpLead._id.toString());
  });

  it('validates pagination query', async () => {
    const invalid = validatePaginationQuery({ page: 0 });
    assert.equal(invalid.valid, false);

    const valid = validatePaginationQuery({ page: 1, limit: 10 });
    assert.equal(valid.valid, true);
  });
});

describe('Dashboard route authentication', () => {
  it('requireAuth rejects missing token', async () => {
    const { error } = await runMiddleware(requireAuth, { headers: {} });
    assert.ok(error instanceof AppError);
    assert.equal(error.statusCode, 401);
  });

  it('requireAuth accepts admin token', async () => {
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
