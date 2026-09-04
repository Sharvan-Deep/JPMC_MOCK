/**
 * Outreach workflow tests with mocked AI HTTP.
 */
require('dotenv').config();

process.env.JWT_ACCESS_SECRET =
  process.env.JWT_ACCESS_SECRET || 'test-access-secret-for-ai-module';
process.env.AI_SERVICE_URL = 'http://localhost:8000';

const { describe, it, before, after, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { User, Company, Lead, OutreachDraft, OutreachSendAudit } = require('../models');
const authService = require('../services/authService');
const app = require('../app');
const { USER_ROLES, OUTREACH_DRAFT_STATUSES } = require('../config/constants');
const { createTestRun } = require('./helpers/testIsolation');
const { requestApp, jsonResponse, installFetchMock } = require('./helpers/httpRequest');

const run = createTestRun();
const draftId = `draft-${run.id}`;
let staffUser;
let company;
let lead;
let accessToken;
let mock;

function outreachFetch() {
  return (entry) => {
    const { url, method } = entry;
    if (url.endsWith('/api/v1/outreach/draft') && method === 'POST') {
      return jsonResponse(200, {
        draft_id: draftId,
        subject: 'Partnership on rural water',
        body: 'We noticed your WASH programmes...',
        evidence_used: [{ company: company.company_name, document_type: 'csr' }],
        unsupported_claims: [],
        warnings: ['Keep claims evidence-backed'],
      });
    }
    if (url.endsWith('/api/v1/outreach/edit')) {
      return jsonResponse(200, {
        draft_id: draftId,
        subject: 'Updated subject',
        body: 'Updated body',
        evidence_used: [{ company: company.company_name, document_type: 'csr' }],
        warnings: [],
      });
    }
    if (url.includes(`/api/v1/outreach/validate/${draftId}`)) {
      return jsonResponse(200, { valid: true, warnings: ['tone check'], unsupported_claims: [] });
    }
    if (url.endsWith('/api/v1/outreach/approve')) {
      return jsonResponse(200, { draft_id: draftId, status: 'APPROVED' });
    }
    if (url.endsWith('/api/v1/outreach/send')) {
      return jsonResponse(200, {
        send_id: `send-${run.id}`,
        status: 'SENT',
        sent_at: new Date().toISOString(),
      });
    }
    return jsonResponse(404, { detail: url });
  };
}

before(async () => {
  await connectDatabase();

  staffUser = await User.create({
    name: 'Outreach Staff',
    email: run.email('out-staff'),
    role: USER_ROLES.FUNDRAISING_STAFF,
    isActive: true,
    isEmailVerified: true,
  });

  company = await Company.create({
    company_name: `Outreach Company ${run.id}`,
    companyNameKey: `outreach-company-${run.id}`,
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
  await OutreachSendAudit.deleteMany({ companyId: company._id });
  await OutreachDraft.deleteMany({ companyId: company._id });
  await Lead.deleteMany({ company: company._id });
  await Company.deleteMany({ companyNameKey: { $regex: run.id } });
  await User.deleteMany({ email: { $regex: run.id } });
  await disconnectDatabase();
});

describe('Outreach workflow', { concurrency: false }, () => {
  it('generates a draft', async () => {
    mock = installFetchMock(outreachFetch());
    const res = await requestApp(app, `/api/leads/${lead._id}/outreach/generate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: { tone: 'professional', recipientRole: 'csr_head' },
    });

    assert.equal(res.status, 201);
    assert.equal(res.json.data.draft.draft_id, draftId);
    assert.equal(res.json.data.human_approval_required, true);

    const stored = await OutreachDraft.findOne({ draft_id: draftId }).lean();
    assert.equal(stored.status, OUTREACH_DRAFT_STATUSES.DRAFT);
    assert.ok(stored.evidence_used.length > 0);
  });

  it('edits a draft and stores revision history', async () => {
    mock = installFetchMock(outreachFetch());
    const res = await requestApp(app, `/api/outreach/${draftId}/edit`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: { subject: 'Updated subject', body: 'Updated body' },
    });

    assert.equal(res.status, 200);
    const stored = await OutreachDraft.findOne({ draft_id: draftId }).lean();
    assert.equal(stored.subject, 'Updated subject');
    assert.ok(stored.revision_history.length >= 1);
  });

  it('rejects send before approval', async () => {
    mock = installFetchMock(outreachFetch());
    const res = await requestApp(app, `/api/outreach/${draftId}/send`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: { recipientEmail: 'csr@example.com' },
    });

    assert.equal(res.status, 403);
    assert.equal(res.json.code, 'OUTREACH_NOT_APPROVED');
    assert.equal(
      mock.calls.some((call) => call.url.endsWith('/api/v1/outreach/send')),
      false
    );
  });

  it('validates, approves, and sends with audit', async () => {
    mock = installFetchMock(outreachFetch());

    const validated = await requestApp(app, `/api/outreach/${draftId}/validate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    assert.equal(validated.status, 200);
    assert.equal(validated.json.data.draft.status, OUTREACH_DRAFT_STATUSES.VALIDATED);

    const approved = await requestApp(app, `/api/outreach/${draftId}/approve`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: {},
    });
    assert.equal(approved.status, 200);
    assert.equal(approved.json.data.draft.status, OUTREACH_DRAFT_STATUSES.APPROVED);
    assert.equal(approved.json.data.draft.approved_by, staffUser._id.toString());

    const sent = await requestApp(app, `/api/outreach/${draftId}/send`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: { recipientEmail: 'csr@example.com' },
    });

    assert.equal(sent.status, 200);
    assert.equal(sent.json.data.audit.send_id, `send-${run.id}`);
    assert.equal(sent.json.data.audit.recipient_email, 'csr@example.com');

    const audit = await OutreachSendAudit.findOne({ send_id: `send-${run.id}` }).lean();
    assert.ok(audit);
    assert.equal(audit.company, company.company_name);
  });

  it('preserves AI 403 on send even after local approval', async () => {
    await OutreachDraft.updateOne(
      { draft_id: draftId },
      { $set: { status: OUTREACH_DRAFT_STATUSES.APPROVED } }
    );

    mock = installFetchMock((entry) => {
      if (entry.url.endsWith('/api/v1/outreach/send')) {
        return jsonResponse(403, { detail: 'Draft is not approved' });
      }
      return jsonResponse(200, {});
    });

    const res = await requestApp(app, `/api/outreach/${draftId}/send`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: { recipientEmail: 'csr@example.com' },
    });

    assert.equal(res.status, 403);
    assert.equal(res.json.code, 'AI_FORBIDDEN');
  });
});
