const { AppError } = require('./errors');
const { AI_ERROR_CODES } = require('../config/constants');

const SECRET_KEY_PATTERN = /(api[_-]?key|authorization|bearer|gemini|openai|chroma|secret|password|token)\s*[:=]\s*['"]?[^'"\s]+/gi;
const FILESYSTEM_PATH_PATTERN = /(?:[A-Za-z]:\\|\/(?:home|Users|var|opt|tmp|usr|app)\/)[^\s'"]+/g;

/**
 * Strip secrets and local filesystem paths from AI error payloads before they reach clients.
 * @param {unknown} value
 * @returns {unknown}
 */
function sanitizeAiPayload(value) {
  if (typeof value === 'string') {
    return value.replace(SECRET_KEY_PATTERN, '[redacted]').replace(FILESYSTEM_PATH_PATTERN, '[redacted-path]');
  }

  if (Array.isArray(value)) {
    return value.map(sanitizeAiPayload);
  }

  if (value && typeof value === 'object') {
    const sanitized = {};

    for (const [key, nested] of Object.entries(value)) {
      if (/key|secret|password|token|authorization/i.test(key)) {
        sanitized[key] = '[redacted]';
        continue;
      }

      sanitized[key] = sanitizeAiPayload(nested);
    }

    return sanitized;
  }

  return value;
}

function extractValidationMessages(body) {
  if (!body || typeof body !== 'object') {
    return [];
  }

  if (Array.isArray(body.detail)) {
    return body.detail.map((item) => {
      if (typeof item === 'string') {
        return item;
      }

      const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
      const msg = item.msg || item.message || JSON.stringify(item);
      return loc ? `${loc}: ${msg}` : String(msg);
    });
  }

  if (typeof body.detail === 'string') {
    return [body.detail];
  }

  if (Array.isArray(body.errors)) {
    return body.errors.map((item) => (typeof item === 'string' ? item : JSON.stringify(item)));
  }

  if (typeof body.message === 'string') {
    return [body.message];
  }

  return [];
}

/**
 * Map Python AI HTTP failures to operational AppErrors.
 * @param {number} status
 * @param {unknown} body
 */
function mapAiHttpError(status, body) {
  const sanitized = sanitizeAiPayload(body);
  const messages = extractValidationMessages(sanitized);
  const fallback = messages[0] || `AI service request failed (${status})`;

  if (status === 422) {
    return new AppError(fallback, 422, {
      code: AI_ERROR_CODES.AI_VALIDATION,
      errors: messages,
      details: sanitized,
    });
  }

  if (status === 403) {
    return new AppError(fallback, 403, {
      code: AI_ERROR_CODES.AI_FORBIDDEN,
      errors: messages,
      details: sanitized,
    });
  }

  if (status === 404) {
    return new AppError(fallback, 404, {
      code: AI_ERROR_CODES.AI_ERROR,
      errors: messages,
      details: sanitized,
    });
  }

  if (status >= 500) {
    return new AppError('AI service is unavailable', 503, {
      code: AI_ERROR_CODES.AI_UNAVAILABLE,
      errors: messages,
    });
  }

  return new AppError(fallback, status >= 400 && status < 500 ? status : 502, {
    code: AI_ERROR_CODES.AI_ERROR,
    errors: messages,
    details: sanitized,
  });
}

function isAbortError(err) {
  return (
    err?.name === 'AbortError' ||
    err?.name === 'TimeoutError' ||
    err?.code === 'ABORT_ERR'
  );
}

function isConnectionError(err) {
  const code = err?.code || err?.cause?.code;
  const message = String(err?.message || err?.cause?.message || '');

  return (
    ['ECONNREFUSED', 'ENOTFOUND', 'EAI_AGAIN', 'ECONNRESET', 'UND_ERR_SOCKET'].includes(code) ||
    message.includes('fetch failed') ||
    message.includes('ECONNREFUSED')
  );
}

module.exports = {
  sanitizeAiPayload,
  mapAiHttpError,
  isAbortError,
  isConnectionError,
};
