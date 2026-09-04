const mongoose = require('mongoose');
const { isValidEmail, normalizeEmail } = require('../utils/email');

const TONES = ['formal', 'professional', 'warm', 'concise'];
const RECIPIENT_ROLES = ['csr_head', 'sustainability_lead', 'ceo', 'foundation_contact', 'other'];

function asOptionalString(value, field, { max = 500 } = {}) {
  if (value === undefined || value === null || value === '') {
    return { valid: true, value: undefined };
  }

  if (typeof value !== 'string') {
    return { valid: false, errors: [`${field} must be a string`] };
  }

  const trimmed = value.trim();
  if (trimmed.length > max) {
    return { valid: false, errors: [`${field} must be at most ${max} characters`] };
  }

  return { valid: true, value: trimmed };
}

function validateObjectId(value, fieldName) {
  if (!value || typeof value !== 'string' || !mongoose.Types.ObjectId.isValid(value)) {
    return { valid: false, errors: [`Invalid ${fieldName}`] };
  }

  return { valid: true, errors: [], value };
}

function validateDiscoverBody(body) {
  const errors = [];
  const query = typeof body?.query === 'string' ? body.query.trim() : typeof body?.search === 'string' ? body.search.trim() : '';

  if (!query) {
    errors.push('query is required');
  }

  let limit;

  if (body?.limit !== undefined && body?.limit !== null && body?.limit !== '') {
    limit = Number(body.limit);
    if (!Number.isInteger(limit) || limit < 1 || limit > 50) {
      errors.push('limit must be an integer between 1 and 50');
    }
  }

  if (errors.length) {
    return { valid: false, errors };
  }

  return { valid: true, errors: [], data: { query, limit } };
}

function validateCopilotChatBody(body) {
  const message = asOptionalString(body?.message, 'message', { max: 4000 });

  if (!body?.message || !message.valid || !message.value) {
    return { valid: false, errors: message.errors.length ? message.errors : ['message is required'] };
  }

  return { valid: true, errors: [], data: { message: message.value } };
}

function validateRecommendBody(body = {}) {
  const notes = asOptionalString(body.notes, 'notes', { max: 2000 });

  if (!notes.valid) {
    return { valid: false, errors: notes.errors };
  }

  return { valid: true, errors: [], data: { notes: notes.value } };
}

function validateOutreachGenerateBody(body = {}) {
  const errors = [];
  const toneResult = asOptionalString(body.tone, 'tone', { max: 50 });
  const roleResult = asOptionalString(body.recipientRole, 'recipientRole', { max: 80 });

  if (!toneResult.valid) errors.push(...toneResult.errors);
  if (!roleResult.valid) errors.push(...roleResult.errors);

  if (toneResult.value && !TONES.includes(toneResult.value.toLowerCase())) {
    errors.push(`tone must be one of: ${TONES.join(', ')}`);
  }

  if (roleResult.value && !RECIPIENT_ROLES.includes(roleResult.value.toLowerCase())) {
    errors.push(`recipientRole must be one of: ${RECIPIENT_ROLES.join(', ')}`);
  }

  if (errors.length) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      tone: toneResult.value ? toneResult.value.toLowerCase() : undefined,
      recipientRole: roleResult.value ? roleResult.value.toLowerCase() : undefined,
    },
  };
}

function validateOutreachEditBody(body = {}) {
  const errors = [];
  const subject = asOptionalString(body.subject, 'subject', { max: 300 });
  const draftBody = asOptionalString(body.body, 'body', { max: 20000 });
  const instruction = asOptionalString(body.instruction, 'instruction', { max: 2000 });
  const tone = asOptionalString(body.tone, 'tone', { max: 50 });

  if (!body || typeof body !== 'object') {
    return { valid: false, errors: ['Request body is required'] };
  }

  if (!subject.valid) errors.push(...subject.errors);
  if (!draftBody.valid) errors.push(...draftBody.errors);
  if (!instruction.valid) errors.push(...instruction.errors);
  if (!tone.valid) errors.push(...tone.errors);

  if (!subject.value && !draftBody.value && !instruction.value) {
    errors.push('subject, body, or instruction is required');
  }

  if (tone.value && !TONES.includes(tone.value.toLowerCase())) {
    errors.push(`tone must be one of: ${TONES.join(', ')}`);
  }

  if (errors.length) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      subject: subject.value,
      body: draftBody.value,
      instruction: instruction.value,
      tone: tone.value ? tone.value.toLowerCase() : undefined,
    },
  };
}

function validateOutreachApproveBody(body = {}) {
  const notes = asOptionalString(body.notes, 'notes', { max: 2000 });
  const approvedByName = asOptionalString(body.approvedByName, 'approvedByName', { max: 150 });

  if (!notes.valid || !approvedByName.valid) {
    return { valid: false, errors: [...(notes.errors || []), ...(approvedByName.errors || [])] };
  }

  return {
    valid: true,
    errors: [],
    data: {
      notes: notes.value,
      approvedByName: approvedByName.value,
    },
  };
}

function validateOutreachSendBody(body = {}) {
  if (!body?.recipientEmail || typeof body.recipientEmail !== 'string' || !isValidEmail(body.recipientEmail)) {
    return { valid: false, errors: ['Valid recipientEmail is required'] };
  }

  return {
    valid: true,
    errors: [],
    data: { recipientEmail: normalizeEmail(body.recipientEmail) },
  };
}

function validateScoreBatchBody(body = {}) {
  if (!Array.isArray(body.leadIds) || body.leadIds.length === 0) {
    return { valid: false, errors: ['leadIds is required'] };
  }

  const ids = [];

  for (const id of body.leadIds) {
    const result = validateObjectId(id, 'leadId');
    if (!result.valid) {
      return { valid: false, errors: result.errors };
    }
    ids.push(result.value);
  }

  return { valid: true, errors: [], data: { leadIds: ids } };
}

function validatePaginationQuery(query = {}) {
  const page = Math.max(1, parseInt(query.page, 10) || 1);
  const rawLimit = parseInt(query.limit, 10) || 20;
  const limit = Math.min(Math.max(1, rawLimit), 100);

  return { valid: true, errors: [], data: { page, limit } };
}

function validateDraftIdParam(value) {
  if (!value || typeof value !== 'string' || !value.trim() || value.trim().length > 200) {
    return { valid: false, errors: ['Invalid draft id'] };
  }

  return { valid: true, errors: [], value: value.trim() };
}

module.exports = {
  TONES,
  RECIPIENT_ROLES,
  validateDiscoverBody,
  validateCopilotChatBody,
  validateRecommendBody,
  validateOutreachGenerateBody,
  validateOutreachEditBody,
  validateOutreachApproveBody,
  validateOutreachSendBody,
  validateScoreBatchBody,
  validatePaginationQuery,
  validateDraftIdParam,
};
