/**
 * Company Management API route mounting tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-company-module';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company } = require('../models');
const authService = require('../services/authService');
const app = require('../app');
const { USER_ROLES } = require('../config/constants');
const { createTestRun } = require('./helpers/testIsolation');

const run = createTestRun();
const email = run.email('company-route');

let staffUser;
let company;
let accessToken;

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, () => {
      const { port } = server.address();

      const req = http.request(
        {
          hostname: '127.0.0.1',
          port,
          path,
          method: options.method || 'GET',
          headers: options.headers || {},
        },
        (res) => {
          const chunks = [];

          res.on('data', (chunk) => chunks.push(chunk));
          res.on('end', () => {
            server.close();
            resolve({
              status: res.statusCode,
              body: Buffer.concat(chunks).toString('utf8'),
            });
          });
        }
      );

      req.on('error', (err) => {
        server.close();
        reject(err);
      });

      req.end();
    });
  });
}

before(async () => {
  await connectDatabase();

  staffUser = await User.create({
    name: 'Company Staff',
    email,
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `Company Route Test ${run.id}`,
    companyNameKey: `company-route-test-${run.id}`,
    financial_years: ['2024-25'],
    states: ['Karnataka'],
    csr_sectors: ['Water'],
    wash_record_count: 2,
    total_wash_spend_crore: 4.5,
    wash_focus_evidence: 'Rural water supply',
  });

  accessToken = authService.createAccessToken(staffUser);
});

after(async () => {
  await Company.deleteMany({ companyNameKey: { $regex: run.id } });
  await User.deleteMany({ email: { $regex: run.id } });
  await disconnectDatabase();
});

describe('Company API route mounting', () => {
  function authHeaders() {
    return { Authorization: `Bearer ${accessToken}` };
  }

  it('GET /api/companies is reachable', async () => {
    const res = await request('/api/companies', { headers: authHeaders() });
    const body = JSON.parse(res.body);

    assert.equal(res.status, 200);
    assert.equal(body.success, true);
    assert.ok(Array.isArray(body.data.companies));
    assert.ok(body.data.pagination);
  });

  it('GET /api/companies/:companyId is reachable', async () => {
    const res = await request(`/api/companies/${company._id}`, { headers: authHeaders() });
    const body = JSON.parse(res.body);

    assert.equal(res.status, 200);
    assert.equal(body.success, true);
    assert.equal(body.data.company.company_name, company.company_name);
    assert.equal(body.data.company.companyNameKey, undefined);
  });

  it('GET /api/companies/:companyId/summary is reachable', async () => {
    const res = await request(`/api/companies/${company._id}/summary`, { headers: authHeaders() });
    const body = JSON.parse(res.body);

    assert.equal(res.status, 200);
    assert.equal(body.success, true);
    assert.equal(body.data.summary.company_name, company.company_name);
    assert.equal(body.data.summary.total_wash_spend_crore, 4.5);
  });

  it('CSR nested route still resolves correctly', async () => {
    const res = await request(`/api/companies/${company._id}/csr`, { headers: authHeaders() });
    const body = JSON.parse(res.body);

    assert.equal(res.status, 200);
    assert.equal(body.success, true);
    assert.equal(body.data.company.company_name, company.company_name);
    assert.ok(body.data.washSummary);
  });
});
