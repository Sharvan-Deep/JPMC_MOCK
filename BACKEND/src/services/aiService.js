const { getAiConfig } = require('../config/ai');
const { AppError } = require('../utils/errors');
const { AI_ERROR_CODES } = require('../config/constants');
const {
  mapAiHttpError,
  isAbortError,
  isConnectionError,
} = require('../utils/aiErrors');

function buildUrl(path, query) {
  const { baseUrl } = getAiConfig();
  const url = new URL(path, `${baseUrl}/`);

  if (query && typeof query === 'object') {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value));
      }
    }
  }

  return url;
}

/**
 * Single HTTP entry point to the Python AI service.
 * @param {string} method
 * @param {string} path
 * @param {{ body?: unknown, query?: Record<string, unknown> }} [options]
 */
async function aiRequest(method, path, options = {}) {
  const { timeoutMs } = getAiConfig();
  const url = buildUrl(path, options.query);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const fetchOptions = {
      method,
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    };

    if (options.body !== undefined) {
      fetchOptions.headers['Content-Type'] = 'application/json';
      fetchOptions.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, fetchOptions);
    const text = await response.text();
    let parsed = null;

    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = { message: text.slice(0, 2000) };
      }
    }

    if (!response.ok) {
      throw mapAiHttpError(response.status, parsed);
    }

    return parsed;
  } catch (err) {
    if (err instanceof AppError) {
      throw err;
    }

    if (isAbortError(err)) {
      throw new AppError('AI service timed out', 503, { code: AI_ERROR_CODES.AI_TIMEOUT });
    }

    if (isConnectionError(err)) {
      throw new AppError('AI service is unavailable', 503, { code: AI_ERROR_CODES.AI_UNAVAILABLE });
    }

    throw new AppError('AI service is unavailable', 503, { code: AI_ERROR_CODES.AI_UNAVAILABLE });
  } finally {
    clearTimeout(timer);
  }
}

function encodePathSegment(value) {
  return encodeURIComponent(String(value));
}

async function health() {
  return aiRequest('GET', '/api/v1/health');
}

async function healthRoot() {
  return aiRequest('GET', '/health');
}

async function validateDocument(body) {
  return aiRequest('POST', '/api/v1/documents/validate', { body });
}

async function extractDocument(body) {
  return aiRequest('POST', '/api/v1/documents/extract', { body });
}

async function preprocessDocument(body) {
  return aiRequest('POST', '/api/v1/documents/preprocess', { body });
}

async function classifyDocument(body) {
  return aiRequest('POST', '/api/v1/documents/classify', { body });
}

async function indexDocument(body) {
  return aiRequest('POST', '/api/v1/documents/index', { body });
}

async function searchDocuments(body) {
  return aiRequest('POST', '/api/v1/documents/search', { body });
}

async function verifyChanges(body) {
  return aiRequest('POST', '/api/v1/documents/verify-changes', { body });
}

async function calculateFreshness(body) {
  return aiRequest('POST', '/api/v1/freshness/calculate', { body });
}

async function getFreshnessCurrent(company) {
  return aiRequest('GET', `/api/v1/freshness/${encodePathSegment(company)}/current`);
}

async function getFreshnessHistory(company) {
  return aiRequest('GET', `/api/v1/freshness/${encodePathSegment(company)}/history`);
}

async function scoreCandidate(body) {
  return aiRequest('POST', '/api/v1/scoring/score', { body });
}

async function scoreCandidatesBatch(body) {
  return aiRequest('POST', '/api/v1/scoring/score-batch', { body });
}

async function getTopCandidates(query) {
  return aiRequest('GET', '/api/v1/scoring/candidates/top', { query });
}

async function recommend(body) {
  return aiRequest('POST', '/api/v1/copilot/recommend', { body });
}

async function getRecommendations(company) {
  return aiRequest('GET', `/api/v1/copilot/recommendations/${encodePathSegment(company)}`);
}

async function copilotChat(body) {
  return aiRequest('POST', '/api/v1/copilot/chat', { body });
}

async function draftOutreach(body) {
  return aiRequest('POST', '/api/v1/outreach/draft', { body });
}

async function editOutreach(body) {
  return aiRequest('POST', '/api/v1/outreach/edit', { body });
}

async function getOutreachDraft(draftId) {
  return aiRequest('GET', `/api/v1/outreach/drafts/${encodePathSegment(draftId)}`);
}

async function validateOutreach(draftId, body) {
  return aiRequest('POST', `/api/v1/outreach/validate/${encodePathSegment(draftId)}`, {
    body: body || {},
  });
}

async function approveOutreach(body) {
  return aiRequest('POST', '/api/v1/outreach/approve', { body });
}

async function sendOutreach(body) {
  return aiRequest('POST', '/api/v1/outreach/send', { body });
}

async function getOutreachAudit(company) {
  return aiRequest('GET', `/api/v1/outreach/audit/${encodePathSegment(company)}`);
}

module.exports = {
  aiRequest,
  health,
  healthRoot,
  validateDocument,
  extractDocument,
  preprocessDocument,
  classifyDocument,
  indexDocument,
  searchDocuments,
  verifyChanges,
  calculateFreshness,
  getFreshnessCurrent,
  getFreshnessHistory,
  scoreCandidate,
  scoreCandidatesBatch,
  getTopCandidates,
  recommend,
  getRecommendations,
  copilotChat,
  draftOutreach,
  editOutreach,
  getOutreachDraft,
  validateOutreach,
  approveOutreach,
  sendOutreach,
  getOutreachAudit,
};
