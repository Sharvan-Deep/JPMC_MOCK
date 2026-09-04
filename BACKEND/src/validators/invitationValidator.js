const { parse } = require('csv-parse/sync');
const { INVITATION_CSV_HEADERS } = require('../config/constants');
const { isValidEmail, normalizeEmail } = require('../utils/email');
const { validatePassword } = require('../utils/password');

/**
 * @param {string} name
 * @returns {{ valid: boolean, errors: string[] }}
 */
function validateName(name) {
  const errors = [];

  if (!name || typeof name !== 'string' || !name.trim()) {
    errors.push('Name is required');
  } else if (name.trim().length > 150) {
    errors.push('Name must be 150 characters or fewer');
  }

  return { valid: errors.length === 0, errors };
}

/**
 * @param {string} email
 * @returns {{ valid: boolean, errors: string[], normalized?: string }}
 */
function validateEmailField(email) {
  if (!email || typeof email !== 'string' || !email.trim()) {
    return { valid: false, errors: ['Email is required'] };
  }

  const normalized = normalizeEmail(email);

  if (!isValidEmail(normalized)) {
    return { valid: false, errors: ['Invalid email address'] };
  }

  return { valid: true, errors: [], normalized };
}

/**
 * @param {{ name?: string, email?: string }} body
 * @returns {{ valid: boolean, errors: string[], data?: { name: string, email: string } }}
 */
function validateCreateInvitationBody(body) {
  const errors = [];
  const nameResult = validateName(body?.name);
  const emailResult = validateEmailField(body?.email);

  errors.push(...nameResult.errors, ...emailResult.errors);

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      name: body.name.trim(),
      email: emailResult.normalized,
    },
  };
}

/**
 * @param {{ token?: string }} body
 * @returns {{ valid: boolean, errors: string[], token?: string }}
 */
function validateTokenBody(body) {
  if (!body?.token || typeof body.token !== 'string' || !body.token.trim()) {
    return { valid: false, errors: ['Token is required'] };
  }

  return { valid: true, errors: [], token: body.token.trim() };
}

/**
 * @param {{ token?: string, name?: string, password?: string }} body
 */
function validateActivationBody(body) {
  const errors = [];
  const tokenResult = validateTokenBody(body);

  if (!tokenResult.valid) {
    errors.push(...tokenResult.errors);
  }

  const passwordResult = validatePassword(body?.password);
  if (!passwordResult.valid) {
    errors.push(...passwordResult.errors);
  }

  let name;
  if (body?.name !== undefined && body?.name !== null && String(body.name).trim() !== '') {
    const nameResult = validateName(body.name);
    if (!nameResult.valid) {
      errors.push(...nameResult.errors);
    } else {
      name = body.name.trim();
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      token: tokenResult.token,
      password: body.password,
      ...(name ? { name } : {}),
    },
  };
}

/**
 * @param {string[]} headers
 * @returns {{ valid: boolean, missing: string[] }}
 */
function validateInvitationCsvHeaders(headers) {
  const normalizedHeaders = headers.map((h) => String(h).trim().toLowerCase());
  const expected = INVITATION_CSV_HEADERS.map((h) => h.toLowerCase());
  const missing = expected.filter((col) => !normalizedHeaders.includes(col));

  return {
    valid: missing.length === 0,
    missing,
  };
}

/**
 * Parse invitation CSV buffer into row objects.
 * @param {Buffer} buffer
 * @returns {{ rows: Record<string, string>[], headers: string[] }}
 */
function parseInvitationCsvBuffer(buffer) {
  const content = buffer.toString('utf8');
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
  });

  const headers = records.length > 0 ? Object.keys(records[0]) : [];

  return { rows: records, headers };
}

module.exports = {
  validateName,
  validateEmailField,
  validateCreateInvitationBody,
  validateTokenBody,
  validateActivationBody,
  validateInvitationCsvHeaders,
  parseInvitationCsvBuffer,
};
