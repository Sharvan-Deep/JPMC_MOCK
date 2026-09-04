/**
 * AI HTTP client tests (no MongoDB).
 */
const { describe, it, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { jsonResponse, installFetchMock } = require('./helpers/httpRequest');

process.env.AI_SERVICE_URL = 'http://localhost:8000';

const aiService = require('../services/aiService');
const { AI_ERROR_CODES } = require('../config/constants');

let mock;

describe('AI client', () => {
  afterEach(() => {
    mock?.restore();
    mock = null;
  });

  it('health maps GET /api/v1/health', async () => {
    mock = installFetchMock(() => jsonResponse(200, { status: 'ok' }));
    const result = await aiService.health();
    assert.equal(result.status, 'ok');
    assert.match(mock.calls[0].url, /\/api\/v1\/health$/);
  });

  it('successful scoring POST returns JSON', async () => {
    mock = installFetchMock(() => jsonResponse(200, { total_score: 82, priority_band: 'HIGH' }));
    const result = await aiService.scoreCandidate({ company_id: 'abc', company: 'Acme' });
    assert.equal(result.total_score, 82);
    assert.equal(mock.calls[0].method, 'POST');
    assert.match(mock.calls[0].url, /\/api\/v1\/scoring\/score$/);
  });

  it('timeout becomes AI_TIMEOUT', async () => {
    const previousTimeout = process.env.AI_SERVICE_TIMEOUT_MS;
    process.env.AI_SERVICE_TIMEOUT_MS = '20';

    mock = installFetchMock((_entry) => {
      return new Promise((_, reject) => {
        setTimeout(() => {
          const err = new Error('aborted');
          err.name = 'AbortError';
          reject(err);
        }, 5);
      });
    });

    try {
      await assert.rejects(
        () => aiService.health(),
        (err) => {
          assert.equal(err.statusCode, 503);
          assert.equal(err.code, AI_ERROR_CODES.AI_TIMEOUT);
          return true;
        }
      );
    } finally {
      if (previousTimeout === undefined) {
        delete process.env.AI_SERVICE_TIMEOUT_MS;
      } else {
        process.env.AI_SERVICE_TIMEOUT_MS = previousTimeout;
      }
    }
  });

  it('connection failure becomes AI_UNAVAILABLE', async () => {
    mock = installFetchMock(() => {
      const err = new Error('fetch failed');
      err.cause = { code: 'ECONNREFUSED' };
      throw err;
    });

    await assert.rejects(
      () => aiService.health(),
      (err) => {
        assert.equal(err.statusCode, 503);
        assert.equal(err.code, AI_ERROR_CODES.AI_UNAVAILABLE);
        return true;
      }
    );
  });

  it('non-2xx 422 preserves validation details', async () => {
    mock = installFetchMock(() =>
      jsonResponse(422, { detail: [{ loc: ['body', 'company_id'], msg: 'field required' }] })
    );

    await assert.rejects(
      () => aiService.scoreCandidate({}),
      (err) => {
        assert.equal(err.statusCode, 422);
        assert.equal(err.code, AI_ERROR_CODES.AI_VALIDATION);
        assert.ok(err.errors[0].includes('company_id'));
        assert.ok(err.details);
        return true;
      }
    );
  });

  it('403 preserves AI_FORBIDDEN', async () => {
    mock = installFetchMock(() => jsonResponse(403, { detail: 'Draft is not approved' }));

    await assert.rejects(
      () => aiService.sendOutreach({ draft_id: 'd1' }),
      (err) => {
        assert.equal(err.statusCode, 403);
        assert.equal(err.code, AI_ERROR_CODES.AI_FORBIDDEN);
        return true;
      }
    );
  });
});
