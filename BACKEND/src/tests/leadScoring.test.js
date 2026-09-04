/**
 * Lead scoring persistence and top-leads tests.
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-ai-module';
process.env.AI_SERVICE_URL = 'http://localhost:8000';

const { describe, it, before, after, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company, Lead, CompanyLeadScore } = require('../models');
const authService = require('../services/authService');
const app = require('../app');
const { USER_ROLES, LEAD_PRIORITIES } = require('../config/constants');
const { createTestRun } = require('./helpers/testIsolation');
const { requestApp, jsonResponse, installFetchMock } = require('./helpers/httpRequest');

const run = createTestRun();
let staffUser;
let otherStaff;
let company;
let lead;
let accessToken;
let otherToken;
let mock;

before(async () => {
  await connectDatabase();

  staffUser = await User.create({
    name: 'Score Staff',
    email: run.email('score-staff'),
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  otherStaff = await User.create({
    name: 'Score Other',
    email: run.email('score-other'),
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `Score Company ${run.id}`,
    companyNameKey: `score-company-${run.id}`,
    total_wash_spend_crore: 8,
    latest_financial_year: '2024-25',
  });

  lead = await Lead.create({
    company: company._id,
    assignedTo: staffUser._id,
    createdBy: staffUser._id,
    priority: LEAD_PRIORITIES.MEDIUM,
  });

  accessToken = authService.createAccessToken(staffUser);
  otherToken = authService.createAccessToken(otherStaff);
});

afterEach(() => {
  mock?.restore();
  mock = null;
});

after(async () => {
  await CompanyLeadScore.deleteMany({ companyId: company._id });
  await Lead.deleteMany({ company: company._id });
  await Company.deleteMany({ companyNameKey: { $regex: run.id } });
  await User.deleteMany({ email: { $regex: run.id } });
  await disconnectDatabase();
});

describe('Lead scoring', { concurrency: false }, () => {
  it('rejects unauthenticated scoring', async () => {
    const res = await requestApp(app, `/api/leads/${lead._id}/score`, { method: 'POST' });
    assert.equal(res.status, 401);
  });

  it('forbids another staff member from scoring an unowned lead', async () => {
    const res = await requestApp(app, `/api/leads/${lead._id}/score`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${otherToken}` },
    });
    assert.equal(res.status, 403);
  });

  it('scores a lead, persists history, and does not overwrite Lead.priority', async () => {
    mock = installFetchMock(() =>
      jsonResponse(200, {
        total_score: 91,
        priority_band: 'HIGH',
        components: { wash: 40 },
        scoring_version: 'v1',
        positive_factors: ['Sustained WASH spend'],
        limiting_factors: [],
        missing_information: [],
        evidence: [{ company: company.company_name, document_type: 'csr' }],
      })
    );

    const res = await requestApp(app, `/api/leads/${lead._id}/score`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    assert.equal(res.status, 200);
    assert.equal(res.json.data.score.total_score, 91);
    assert.equal(res.json.data.leadPriorityUnchanged, LEAD_PRIORITIES.MEDIUM);

    const storedLead = await Lead.findById(lead._id).lean();
    assert.equal(storedLead.priority, LEAD_PRIORITIES.MEDIUM);

    const storedCompany = await Company.findById(company._id).lean();
    assert.equal(storedCompany.leadScore.total_score, 91);

    const history = await CompanyLeadScore.find({ companyId: company._id });
    assert.equal(history.length, 1);
    assert.match(mock.calls[0].url, /\/api\/v1\/scoring\/score$/);
  });

  it('GET /api/leads/top uses stored scores without calling AI', async () => {
    mock = installFetchMock(() => jsonResponse(500, { detail: 'should not be called' }));

    const res = await requestApp(app, '/api/leads/top', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    assert.equal(res.status, 200);
    assert.equal(String(res.json.data.leads[0].id), lead._id.toString());
    assert.equal(res.json.data.leads[0].company.leadScore.total_score, 91);
    assert.equal(mock.calls.length, 0);
  });
});
