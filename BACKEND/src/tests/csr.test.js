/**
 * CSR Policy + Source API tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-csr-module';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company, CSRPolicy, Source } = require('../models');
const csrService = require('../services/csrService');
const requireAuth = require('../middleware/requireAuth');
const requireRole = require('../middleware/requireRole');
const authService = require('../services/authService');
const { AppError } = require('../utils/errors');
const { USER_ROLES } = require('../config/constants');
const {
  validateListPoliciesQuery,
  validateListSourcesQuery,
  validateObjectId,
} = require('../validators/csrValidator');
const { createTestRun } = require('./helpers/testIsolation');

const run = createTestRun();
const emails = {
  admin: run.email('csr-admin'),
  staff: run.email('csr-staff'),
};

let adminUser;
let staffUser;
let company;
let otherCompany;
let emptyCompany;
let policy2025;
let policy2024;
let otherCompanyPolicy;
let sourceRecord;

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
    name: 'CSR Admin',
    email: emails.admin,
    role: USER_ROLES.ADMIN,
    isActive: true,
    isEmailVerified: true,
  });

  staffUser = await User.create({
    name: 'CSR Staff',
    email: emails.staff,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `CSR Test Company ${run.id}`,
    companyNameKey: `csr-test-company-${run.id}`,
    financial_years: ['2024-25'],
    states: ['Maharashtra'],
    csr_sectors: ['Water'],
    wash_record_count: 3,
    total_wash_spend_crore: 1.5,
    wash_focus_evidence: 'Water for schools initiative',
  });

  otherCompany = await Company.create({
    company_name: `CSR Other Company ${run.id}`,
    companyNameKey: `csr-other-company-${run.id}`,
  });

  emptyCompany = await Company.create({
    company_name: `CSR Empty Company ${run.id}`,
    companyNameKey: `csr-empty-company-${run.id}`,
  });

  policy2025 = await CSRPolicy.create({
    company: company._id,
    financialYear: '2025-26',
    title: 'CSR Policy 2025-26',
    policyText: 'Focus on drinking water and sanitation.',
    policyUrl: 'https://example.com/policy-2025',
    source: 'Company website',
    retrievedAt: new Date('2025-01-15'),
  });

  policy2024 = await CSRPolicy.create({
    company: company._id,
    financialYear: '2024-25',
    title: 'CSR Policy 2024-25',
    policyText: 'WASH programs in rural schools.',
    policyUrl: 'https://example.com/policy-2024',
    source: 'Annual report',
    retrievedAt: new Date('2024-06-01'),
  });

  otherCompanyPolicy = await CSRPolicy.create({
    company: otherCompany._id,
    financialYear: '2025-26',
    title: 'Other Company Policy',
    policyText: 'Should not be accessible via primary company URL.',
  });

  sourceRecord = await Source.create({
    company: company._id,
    sourceType: 'ANNUAL_REPORT',
    sourceName: 'Annual Report 2024-25',
    sourceUrl: 'https://example.com/annual-report',
    retrievedAt: new Date('2024-08-01'),
  });

  await Source.create({
    company: company._id,
    sourceType: 'WEBSITE',
    sourceName: 'Company CSR Page',
    sourceUrl: 'https://example.com/csr',
    retrievedAt: new Date('2025-02-01'),
  });
});

after(async () => {
  const companyIds = [company?._id, otherCompany?._id, emptyCompany?._id].filter(Boolean);

  if (companyIds.length > 0) {
    await CSRPolicy.deleteMany({ company: { $in: companyIds } });
    await Source.deleteMany({ company: { $in: companyIds } });
    await Company.deleteMany({ _id: { $in: companyIds } });
  }

  await User.deleteMany(run.emailFilter());
  await disconnectDatabase();
});

describe('CSR Policy + Source APIs', () => {
  it('returns CSR overview for an existing company', async () => {
    const overview = await csrService.getCsrOverview(company._id.toString());

    assert.equal(overview.company.company_name, company.company_name);
    assert.equal(overview.policyCount, 2);
    assert.equal(overview.sourceCount, 2);
    assert.ok(overview.availableFinancialYears.includes('2024-25'));
    assert.ok(overview.availableFinancialYears.includes('2025-26'));
    assert.equal(overview.washSummary.wash_record_count, 3);
    assert.ok(Array.isArray(overview.recentPolicies));
    assert.equal(overview.activities.count, 0);
    assert.equal(overview.activities.totalSpendCrore, 0);
    assert.ok(Array.isArray(overview.activities.recent));
  });

  it('lists CSR policies with pagination', async () => {
    const result = await csrService.listPolicies(company._id.toString(), {
      page: 1,
      limit: 1,
    });

    assert.equal(result.policies.length, 1);
    assert.equal(result.pagination.page, 1);
    assert.equal(result.pagination.limit, 1);
    assert.equal(result.pagination.total, 2);
    assert.equal(result.pagination.totalPages, 2);
  });

  it('filters CSR policies by financial year', async () => {
    const result = await csrService.listPolicies(company._id.toString(), {
      financialYear: '2025-26',
    });

    assert.equal(result.policies.length, 1);
    assert.equal(result.policies[0].financialYear, '2025-26');
    assert.equal(result.policies[0].title, 'CSR Policy 2025-26');
  });

  it('returns a single CSR policy', async () => {
    const policy = await csrService.getPolicyById(
      company._id.toString(),
      policy2025._id.toString()
    );

    assert.equal(policy.title, 'CSR Policy 2025-26');
    assert.equal(policy.policyText, 'Focus on drinking water and sanitation.');
    assert.equal(policy.passwordHash, undefined);
  });

  it('prevents accessing a policy through another company URL', async () => {
    await assert.rejects(
      () =>
        csrService.getPolicyById(
          company._id.toString(),
          otherCompanyPolicy._id.toString()
        ),
      (err) => err.statusCode === 404 && err.code === 'CSR_POLICY_NOT_FOUND'
    );
  });

  it('lists sources with pagination', async () => {
    const result = await csrService.listSources(company._id.toString(), {
      page: 1,
      limit: 10,
    });

    assert.equal(result.sources.length, 2);
    assert.equal(result.pagination.total, 2);
    assert.equal(result.sources[0].passwordHash, undefined);
  });

  it('filters sources by sourceType', async () => {
    const result = await csrService.listSources(company._id.toString(), {
      sourceType: 'ANNUAL_REPORT',
    });

    assert.equal(result.sources.length, 1);
    assert.equal(result.sources[0].sourceName, 'Annual Report 2024-25');
  });

  it('rejects unknown company', async () => {
    await assert.rejects(
      () => csrService.getCsrOverview('507f1f77bcf86cd799439011'),
      (err) => err.statusCode === 404 && err.code === 'COMPANY_NOT_FOUND'
    );
  });

  it('rejects invalid companyId', async () => {
    const validation = validateObjectId('bad-id', 'companyId');
    assert.equal(validation.valid, false);
  });

  it('rejects invalid policyId lookup for unknown policy', async () => {
    await assert.rejects(
      () =>
        csrService.getPolicyById(
          company._id.toString(),
          '507f1f77bcf86cd799439011'
        ),
      (err) => err.statusCode === 404
    );
  });

  it('returns empty collections when no policies exist', async () => {
    const result = await csrService.listPolicies(emptyCompany._id.toString(), {
      page: 1,
      limit: 10,
    });

    assert.deepEqual(result.policies, []);
    assert.equal(result.pagination.total, 0);
  });

  it('validates policy list query', async () => {
    const invalid = validateListPoliciesQuery({ sort: 'bad-field' });
    assert.equal(invalid.valid, false);

    const valid = validateListPoliciesQuery({
      page: 1,
      limit: 10,
      financialYear: '2025-26',
      sort: 'financialYear',
      order: 'asc',
    });
    assert.equal(valid.valid, true);
  });

  it('validates source list query', async () => {
    const invalid = validateListSourcesQuery({ order: 'sideways' });
    assert.equal(invalid.valid, false);

    const valid = validateListSourcesQuery({
      sourceType: 'WEBSITE',
      sort: 'sourceName',
    });
    assert.equal(valid.valid, true);
  });
});

describe('CSR route authentication', () => {
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

  it('requireRole allows fundraising staff read access', async () => {
    const middleware = requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF);
    const { error, nextCalled } = await runMiddleware(middleware, {
      user: { role: USER_ROLES.FUNDRAISING_STAFF },
    });

    assert.equal(error, null);
    assert.equal(nextCalled, true);
  });
});
