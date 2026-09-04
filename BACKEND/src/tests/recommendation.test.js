/**
 * Recommendation generation and persistence tests.
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-ai-module';
process.env.AI_SERVICE_URL = 'http://localhost:8000';

const { describe, it, before, after, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company, Lead, CompanyRecommendation } = require('../models');
const authService = require('../services/authService');
const app = require('../app');
const { USER_ROLES } = require('../config/constants');
const { createTestRun } = require('./helpers/testIsolation');
const { requestApp, jsonResponse, installFetchMock } = require('./helpers/httpRequest');

const run = createTestRun();
let staffUser;
let company;
let lead;
let accessToken;
let mock;

before(async () => {
  await connectDatabase();

  staffUser = await User.create({
    name: 'Rec Staff',
    email: run.email('rec-staff'),
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `Rec Company ${run.id}`,
    companyNameKey: `rec-company-${run.id}`,
  });

  lead = await Lead.create({
    company: company._id,
    assignedTo: staffUser._id,
    createdBy: staffUser._id,
  });

  accessToken = authService.createAccessToken(staffUser);
});

afterEach(() => {
  mock?.restore();
  mock = null;
});

after(async () => {
  await CompanyRecommendation.deleteMany({ companyId: company._id });
  await Lead.deleteMany({ company: company._id });
  await Company.deleteMany({ companyNameKey: { $regex: run.id } });
  await User.deleteMany({ email: { $regex: run.id } });
  await disconnectDatabase();
});

describe('Recommendations', { concurrency: false }, () => {
  it('generates and persists a recommendation', async () => {
    mock = installFetchMock(() =>
      jsonResponse(200, {
        recommendation_id: `rec-${run.id}`,
        recommended_action: 'Initiate CSR conversation',
        priority_level: 'HIGH',
        confidence: 0.8,
        reasons: ['Recent WASH spend'],
        positive_factors: ['Water projects'],
        limiting_factors: [],
        missing_information: [],
        evidence_sources: [{ company: company.company_name, document_type: 'csr' }],
        human_approval_required: true,
        advisory_notice: 'Human approval required before outreach.',
      })
    );

    const res = await requestApp(app, `/api/leads/${lead._id}/recommend`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: { notes: 'Focus on rural water' },
    });

    assert.equal(res.status, 200);
    assert.equal(res.json.data.human_approval_required, true);
    assert.equal(res.json.data.recommendation.recommended_action, 'Initiate CSR conversation');

    const stored = await Company.findById(company._id).lean();
    assert.equal(stored.latestRecommendation.recommendation_id, `rec-${run.id}`);

    const history = await CompanyRecommendation.find({ companyId: company._id });
    assert.equal(history.length, 1);
  });

  it('lists stored recommendations for the company', async () => {
    const res = await requestApp(app, `/api/companies/${company._id}/recommendations`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    assert.equal(res.status, 200);
    assert.equal(res.json.data.recommendations.length, 1);
  });
});
