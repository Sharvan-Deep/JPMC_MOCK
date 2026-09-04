/**
 * Company AI analyze/verify persistence tests.
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-ai-module';
process.env.AI_SERVICE_URL = 'http://localhost:8000';

const { describe, it, before, after, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const {
  User,
  Company,
  CompanyFreshnessHistory,
} = require('../models');
const authService = require('../services/authService');
const app = require('../app');
const { USER_ROLES } = require('../config/constants');
const { createTestRun } = require('./helpers/testIsolation');
const { requestApp, jsonResponse, installFetchMock } = require('./helpers/httpRequest');

const run = createTestRun();
let staffUser;
let otherStaff;
let company;
let accessToken;
let otherToken;
let mock;

function routeFor(pathname) {
  return (entry) => {
    const url = entry.url;
    if (url.endsWith('/api/v1/documents/validate')) {
      return jsonResponse(200, { valid: true, warnings: ['soft warning'] });
    }
    if (url.endsWith('/api/v1/documents/classify')) {
      return jsonResponse(200, { document_type: 'csr_summary', evidence: [{ company: company.company_name, document_type: 'csr' }] });
    }
    if (url.endsWith('/api/v1/documents/search')) {
      return jsonResponse(200, { results: [{ company: company.company_name }] });
    }
    if (url.endsWith('/api/v1/documents/verify-changes')) {
      return jsonResponse(200, { changed: false, warnings: [] });
    }
    if (url.endsWith('/api/v1/freshness/calculate')) {
      return jsonResponse(200, {
        status: 'CURRENT',
        verification_cycle: 1,
        verified_at: new Date().toISOString(),
        evidence: [{ company: company.company_name, financial_year: '2024-25' }],
      });
    }
    return jsonResponse(404, { detail: `unmocked ${url}` });
  };
}

before(async () => {
  await connectDatabase();

  staffUser = await User.create({
    name: 'AI Staff',
    email: run.email('ai-staff'),
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  otherStaff = await User.create({
    name: 'AI Other',
    email: run.email('ai-other'),
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `AI Company ${run.id}`,
    companyNameKey: `ai-company-${run.id}`,
    wash_focus_evidence: 'Rural drinking water',
    latest_financial_year: '2024-25',
    total_wash_spend_crore: 3.2,
    financial_years: ['2024-25'],
  });

  accessToken = authService.createAccessToken(staffUser);
  otherToken = authService.createAccessToken(otherStaff);
});

afterEach(() => {
  mock?.restore();
  mock = null;
});

after(async () => {
  await CompanyFreshnessHistory.deleteMany({ companyId: company._id });
  await Company.deleteMany({ companyNameKey: { $regex: run.id } });
  await User.deleteMany({ email: { $regex: run.id } });
  await disconnectDatabase();
});

describe('Company AI integration', { concurrency: false }, () => {
  it('rejects unauthenticated analyze', async () => {
    const res = await requestApp(app, `/api/companies/${company._id}/analyze`, { method: 'POST' });
    assert.equal(res.status, 401);
  });

  it('analyzes a company and persists aiReadySummary', async () => {
    mock = installFetchMock(routeFor());
    const res = await requestApp(app, `/api/companies/${company._id}/analyze`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    assert.equal(res.status, 200);
    assert.equal(res.json.success, true);
    assert.ok(res.json.data.aiReadySummary.classification);
    assert.ok(res.json.data.aiReadySummary.warnings.includes('soft warning'));

    const stored = await Company.findById(company._id).lean();
    assert.ok(stored.aiReadySummary);
    assert.equal(stored.aiReadySummary.classification.document_type, 'csr_summary');
  });

  it('verifies a company and appends freshness history', async () => {
    mock = installFetchMock(routeFor());
    const res = await requestApp(app, `/api/companies/${company._id}/verify`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    assert.equal(res.status, 200);
    assert.equal(res.json.data.freshness.status, 'CURRENT');

    const stored = await Company.findById(company._id).lean();
    assert.equal(stored.freshness.status, 'CURRENT');
    assert.ok(stored.freshness.evidence.length > 0);

    const history = await CompanyFreshnessHistory.find({ companyId: company._id });
    assert.ok(history.length >= 1);
  });

  it('GET freshness returns persisted snapshot', async () => {
    const res = await requestApp(app, `/api/companies/${company._id}/freshness`, {
      headers: { Authorization: `Bearer ${otherToken}` },
    });
    assert.equal(res.status, 200);
    assert.equal(res.json.data.freshness.status, 'CURRENT');
  });
});
