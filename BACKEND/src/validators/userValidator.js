const mongoose = require('mongoose');
const { USER_ROLES } = require('../config/constants');

const SORTABLE_USER_FIELDS = [
  'name',
  'email',
  'role',
  'isActive',
  'createdAt',
  'updatedAt',
  'lastLoginAt',
];

const PROTECTED_USER_FIELDS = [
  'email',
  'role',
  'isActive',
  'passwordHash',
  'googleId',
  'isEmailVerified',
  'lastLoginAt',
];

/**
 * @param {string} name
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
 * @param {Record<string, unknown>} query
 */
function validateListUsersQuery(query = {}) {
  const errors = [];
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const data = { page, limit };

  if (query.search) {
    data.search = String(query.search).trim();
  }

  if (query.role) {
    const role = String(query.role).toUpperCase();

    if (!Object.values(USER_ROLES).includes(role)) {
      errors.push('Invalid role filter');
    } else {
      data.role = role;
    }
  }

  if (query.isActive !== undefined && query.isActive !== null && query.isActive !== '') {
    const value = String(query.isActive).toLowerCase();

    if (!['true', 'false'].includes(value)) {
      errors.push('isActive must be true or false');
    } else {
      data.isActive = value === 'true';
    }
  }

  if (query.sort) {
    if (!SORTABLE_USER_FIELDS.includes(String(query.sort))) {
      errors.push('Invalid sort field');
    } else {
      data.sort = String(query.sort);
    }
  }

  if (query.order) {
    const order = String(query.order).toLowerCase();

    if (!['asc', 'desc'].includes(order)) {
      errors.push('Invalid sort order');
    } else {
      data.order = order;
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return { valid: true, errors: [], data };
}

/**
 * @param {Record<string, unknown>} body
 */
function validateUpdateUserBody(body) {
  if (!body || typeof body !== 'object') {
    return { valid: false, errors: ['Request body is required'] };
  }

  const disallowedFields = PROTECTED_USER_FIELDS.filter((field) => body[field] !== undefined);

  if (disallowedFields.length > 0) {
    return {
      valid: false,
      errors: [`Cannot update protected fields: ${disallowedFields.join(', ')}`],
    };
  }

  const nameResult = validateName(body.name);

  if (!nameResult.valid) {
    return { valid: false, errors: nameResult.errors };
  }

  return {
    valid: true,
    errors: [],
    data: { name: body.name.trim() },
  };
}

/**
 * @param {{ role?: string }} body
 */
function validateRoleBody(body) {
  if (!body?.role || typeof body.role !== 'string') {
    return { valid: false, errors: ['role is required'] };
  }

  const role = String(body.role).toUpperCase();

  if (!Object.values(USER_ROLES).includes(role)) {
    return { valid: false, errors: ['Invalid role'] };
  }

  return { valid: true, errors: [], data: { role } };
}

/**
 * @param {{ isActive?: unknown }} body
 */
function validateStatusBody(body) {
  if (body?.isActive === undefined || body?.isActive === null) {
    return { valid: false, errors: ['isActive is required'] };
  }

  if (typeof body.isActive !== 'boolean') {
    return { valid: false, errors: ['isActive must be a boolean'] };
  }

  return { valid: true, errors: [], data: { isActive: body.isActive } };
}

module.exports = {
  validateListUsersQuery,
  validateUpdateUserBody,
  validateRoleBody,
  validateStatusBody,
  validateName,
};
