const mongoose = require('mongoose');
const {
  LEAD_STATUSES,
  LEAD_PRIORITIES,
  LEAD_ACTIVITY_TYPES,
} = require('../config/constants');

const MANUAL_ACTIVITY_TYPES = Object.values(LEAD_ACTIVITY_TYPES).filter(
  (type) => type !== LEAD_ACTIVITY_TYPES.STATUS_CHANGED
);

const SORTABLE_LEAD_FIELDS = ['createdAt', 'updatedAt', 'status', 'priority'];

/**
 * @param {unknown} value
 * @param {string} fieldName
 */
function validateObjectId(value, fieldName) {
  if (!value || typeof value !== 'string' || !mongoose.Types.ObjectId.isValid(value)) {
    return { valid: false, errors: [`Invalid ${fieldName}`] };
  }

  return { valid: true, errors: [], value };
}

/**
 * @param {{ companyId?: string, priority?: string }} body
 */
function validateCreateLeadBody(body) {
  const errors = [];
  const companyResult = validateObjectId(body?.companyId, 'companyId');

  if (!companyResult.valid) {
    errors.push(...companyResult.errors);
  }

  let priority;

  if (body?.priority !== undefined && body?.priority !== null && body?.priority !== '') {
    priority = String(body.priority).toUpperCase();

    if (!Object.values(LEAD_PRIORITIES).includes(priority)) {
      errors.push('Invalid priority');
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      companyId: companyResult.value,
      priority,
    },
  };
}

/**
 * @param {{ status?: string, priority?: string, assignedTo?: string }} body
 */
function validateUpdateLeadBody(body) {
  const errors = [];
  const data = {};

  if (!body || typeof body !== 'object') {
    return { valid: false, errors: ['Request body is required'] };
  }

  if (body.status !== undefined) {
    const status = String(body.status).toUpperCase();

    if (!Object.values(LEAD_STATUSES).includes(status)) {
      errors.push('Invalid status');
    } else {
      data.status = status;
    }
  }

  if (body.priority !== undefined) {
    const priority = String(body.priority).toUpperCase();

    if (!Object.values(LEAD_PRIORITIES).includes(priority)) {
      errors.push('Invalid priority');
    } else {
      data.priority = priority;
    }
  }

  if (body.assignedTo !== undefined) {
    const assigneeResult = validateObjectId(body.assignedTo, 'assignedTo');

    if (!assigneeResult.valid) {
      errors.push(...assigneeResult.errors);
    } else {
      data.assignedTo = assigneeResult.value;
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  if (Object.keys(data).length === 0) {
    return { valid: false, errors: ['At least one updatable field is required'] };
  }

  return { valid: true, errors: [], data };
}

/**
 * @param {{ userId?: string }} body
 */
function validateAssignLeadBody(body) {
  const result = validateObjectId(body?.userId, 'userId');

  if (!result.valid) {
    return { valid: false, errors: result.errors };
  }

  return {
    valid: true,
    errors: [],
    data: { userId: result.value },
  };
}

/**
 * @param {{ note?: string }} body
 */
function validateCreateNoteBody(body) {
  if (!body?.note || typeof body.note !== 'string' || !body.note.trim()) {
    return { valid: false, errors: ['Note is required'] };
  }

  if (body.note.trim().length > 5000) {
    return { valid: false, errors: ['Note must be 5000 characters or fewer'] };
  }

  return {
    valid: true,
    errors: [],
    data: { note: body.note.trim() },
  };
}

/**
 * @param {{ activityType?: string, description?: string }} body
 */
function validateCreateActivityBody(body) {
  const errors = [];

  if (!body?.activityType || typeof body.activityType !== 'string') {
    errors.push('activityType is required');
  } else {
    const activityType = String(body.activityType).toUpperCase();

    if (!MANUAL_ACTIVITY_TYPES.includes(activityType)) {
      errors.push('Invalid activityType');
    }
  }

  if (body?.description !== undefined && body.description !== null) {
    if (typeof body.description !== 'string') {
      errors.push('description must be a string');
    } else if (body.description.length > 2000) {
      errors.push('description must be 2000 characters or fewer');
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    data: {
      activityType: String(body.activityType).toUpperCase(),
      description: body.description ? String(body.description).trim() : '',
    },
  };
}

/**
 * @param {Record<string, unknown>} query
 */
function validateListLeadsQuery(query = {}) {
  const errors = [];
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const data = { page, limit };

  if (query.status) {
    const status = String(query.status).toUpperCase();

    if (!Object.values(LEAD_STATUSES).includes(status)) {
      errors.push('Invalid status filter');
    } else {
      data.status = status;
    }
  }

  if (query.priority) {
    const priority = String(query.priority).toUpperCase();

    if (!Object.values(LEAD_PRIORITIES).includes(priority)) {
      errors.push('Invalid priority filter');
    } else {
      data.priority = priority;
    }
  }

  if (query.assignedTo) {
    const assigneeResult = validateObjectId(String(query.assignedTo), 'assignedTo');

    if (!assigneeResult.valid) {
      errors.push(...assigneeResult.errors);
    } else {
      data.assignedTo = assigneeResult.value;
    }
  }

  if (query.search) {
    data.search = String(query.search).trim();
  }

  if (query.sort) {
    if (!SORTABLE_LEAD_FIELDS.includes(String(query.sort))) {
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

module.exports = {
  validateCreateLeadBody,
  validateUpdateLeadBody,
  validateAssignLeadBody,
  validateCreateNoteBody,
  validateCreateActivityBody,
  validateListLeadsQuery,
  validateObjectId,
};
