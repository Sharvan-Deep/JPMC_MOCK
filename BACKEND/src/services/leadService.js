const mongoose = require('mongoose');
const { Lead, LeadNote, LeadActivity, Company, User } = require('../models');
const { AppError } = require('../utils/errors');
const { toSafeUser } = require('../utils/userSerializer');
const {
  USER_ROLES,
  LEAD_STATUSES,
  ACTIVE_LEAD_STATUSES,
  LEAD_ACTIVITY_TYPES,
} = require('../config/constants');

const COMPANY_SUMMARY_FIELDS =
  'company_name states csr_sectors latest_financial_year total_wash_spend_crore wash_record_count';
const USER_POPULATE_FIELDS = 'name email role isActive';

function isAdmin(user) {
  return user.role === USER_ROLES.ADMIN;
}

/**
 * @param {import('mongoose').Document | object} lead
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
function canManageLead(lead, user) {
  if (isAdmin(user)) {
    return true;
  }

  const userId = user._id.toString();
  const assignedId = lead.assignedTo?._id?.toString() || lead.assignedTo?.toString();
  const createdId = lead.createdBy?._id?.toString() || lead.createdBy?.toString();

  return assignedId === userId || createdId === userId;
}

/**
 * @param {import('mongoose').Document | object | null} company
 */
function toCompanySummary(company) {
  if (!company) {
    return null;
  }

  const obj = company.toObject ? company.toObject() : company;

  return {
    id: obj._id,
    company_name: obj.company_name,
    states: obj.states,
    csr_sectors: obj.csr_sectors,
    latest_financial_year: obj.latest_financial_year,
    total_wash_spend_crore: obj.total_wash_spend_crore,
    wash_record_count: obj.wash_record_count,
  };
}

/**
 * @param {import('mongoose').Document | object} lead
 */
function toSafeLead(lead) {
  const obj = lead.toObject ? lead.toObject() : lead;

  return {
    id: obj._id,
    company: toCompanySummary(obj.company),
    assignedTo: toSafeUser(obj.assignedTo),
    createdBy: toSafeUser(obj.createdBy),
    status: obj.status,
    priority: obj.priority,
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

/**
 * @param {import('mongoose').Document | object} note
 */
function toSafeNote(note) {
  const obj = note.toObject ? note.toObject() : note;

  return {
    id: obj._id,
    lead: obj.lead,
    user: toSafeUser(obj.user),
    note: obj.note,
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

/**
 * @param {import('mongoose').Document | object} activity
 */
function toSafeActivity(activity) {
  const obj = activity.toObject ? activity.toObject() : activity;

  return {
    id: obj._id,
    lead: obj.lead,
    user: toSafeUser(obj.user),
    activityType: obj.activityType,
    description: obj.description,
    createdAt: obj.createdAt,
  };
}

/**
 * @param {string} leadId
 */
async function getLeadDocumentOrThrow(leadId) {
  const lead = await Lead.findById(leadId);

  if (!lead) {
    throw new AppError('Lead not found', 404, { code: 'LEAD_NOT_FOUND' });
  }

  return lead;
}

/**
 * @param {import('mongoose').Document} lead
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
function assertCanManageLead(lead, user) {
  if (!canManageLead(lead, user)) {
    throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
  }
}

/**
 * @param {string} companyId
 */
async function findActiveLeadForCompany(companyId) {
  return Lead.findOne({
    company: companyId,
    status: { $in: ACTIVE_LEAD_STATUSES },
  });
}

/**
 * @param {string} userId
 */
async function validateAssignableUser(userId) {
  if (!mongoose.Types.ObjectId.isValid(userId)) {
    throw new AppError('Invalid userId', 400, { code: 'INVALID_ID' });
  }

  const targetUser = await User.findById(userId);

  if (!targetUser) {
    throw new AppError('User not found', 404, { code: 'USER_NOT_FOUND' });
  }

  if (!targetUser.isActive) {
    throw new AppError('Cannot assign lead to inactive user', 400, {
      code: 'USER_INACTIVE',
    });
  }

  if (![USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF].includes(targetUser.role)) {
    throw new AppError('User does not have an eligible role for lead assignment', 400, {
      code: 'INVALID_ASSIGNMENT_ROLE',
    });
  }

  return targetUser;
}

/**
 * @param {string} leadId
 */
async function getLeadById(leadId) {
  const lead = await Lead.findById(leadId)
    .populate('company', COMPANY_SUMMARY_FIELDS)
    .populate('assignedTo', USER_POPULATE_FIELDS)
    .populate('createdBy', USER_POPULATE_FIELDS);

  if (!lead) {
    throw new AppError('Lead not found', 404, { code: 'LEAD_NOT_FOUND' });
  }

  const [notes, activities] = await Promise.all([
    LeadNote.find({ lead: leadId })
      .sort({ createdAt: 1 })
      .populate('user', USER_POPULATE_FIELDS)
      .lean(),
    LeadActivity.find({ lead: leadId })
      .sort({ createdAt: 1 })
      .populate('user', USER_POPULATE_FIELDS)
      .lean(),
  ]);

  return {
    lead: toSafeLead(lead),
    notes: notes.map(toSafeNote),
    activities: activities.map(toSafeActivity),
  };
}

/**
 * @param {{ companyId: string, priority?: string }} data
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
async function createLead({ companyId, priority }, user) {
  const company = await Company.findById(companyId);

  if (!company) {
    throw new AppError('Company not found', 404, { code: 'COMPANY_NOT_FOUND' });
  }

  const existing = await findActiveLeadForCompany(companyId);

  if (existing) {
    throw new AppError('An active lead already exists for this company', 409, {
      code: 'ACTIVE_LEAD_EXISTS',
    });
  }

  const leadData = {
    company: companyId,
    createdBy: user._id,
    assignedTo: user._id,
    status: LEAD_STATUSES.NEW,
  };

  if (priority) {
    leadData.priority = priority;
  }

  try {
    const lead = await Lead.create(leadData);
    return getLeadById(lead._id.toString());
  } catch (err) {
    if (err.code === 11000) {
      throw new AppError('An active lead already exists for this company', 409, {
        code: 'ACTIVE_LEAD_EXISTS',
      });
    }

    throw err;
  }
}

/**
 * @param {Record<string, unknown>} query
 */
async function listLeads(query) {
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const skip = (page - 1) * limit;
  const filter = {};

  if (query.status) {
    filter.status = query.status;
  }

  if (query.priority) {
    filter.priority = query.priority;
  }

  if (query.assignedTo) {
    filter.assignedTo = query.assignedTo;
  }

  if (query.search) {
    const term = String(query.search).trim();

    if (term) {
      const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
      const companies = await Company.find({ company_name: regex }).select('_id').lean();
      filter.company = { $in: companies.map((company) => company._id) };
    }
  }

  const sortField = ['createdAt', 'updatedAt', 'status', 'priority'].includes(query.sort)
    ? query.sort
    : 'createdAt';
  const sortOrder = String(query.order || 'desc').toLowerCase() === 'asc' ? 1 : -1;

  const [leads, total] = await Promise.all([
    Lead.find(filter)
      .sort({ [sortField]: sortOrder })
      .skip(skip)
      .limit(limit)
      .populate('company', COMPANY_SUMMARY_FIELDS)
      .populate('assignedTo', USER_POPULATE_FIELDS)
      .populate('createdBy', USER_POPULATE_FIELDS)
      .lean(),
    Lead.countDocuments(filter),
  ]);

  return {
    leads: leads.map(toSafeLead),
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit) || 0,
    },
  };
}

/**
 * @param {string} leadId
 * @param {{ status?: string, priority?: string, assignedTo?: string }} updates
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
async function updateLead(leadId, updates, user) {
  const lead = await getLeadDocumentOrThrow(leadId);
  assertCanManageLead(lead, user);

  const previousStatus = lead.status;

  if (updates.status !== undefined) {
    lead.status = updates.status;
  }

  if (updates.priority !== undefined) {
    lead.priority = updates.priority;
  }

  if (updates.assignedTo !== undefined) {
    if (!isAdmin(user)) {
      throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
    }

    await validateAssignableUser(updates.assignedTo);
    lead.assignedTo = updates.assignedTo;
  }

  await lead.save();

  if (updates.status !== undefined && updates.status !== previousStatus) {
    await LeadActivity.create({
      lead: lead._id,
      user: user._id,
      activityType: LEAD_ACTIVITY_TYPES.STATUS_CHANGED,
      description: `Status changed from ${previousStatus} to ${updates.status}`,
    });
  }

  return getLeadById(leadId);
}

/**
 * @param {string} leadId
 * @param {string} userId
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
async function assignLead(leadId, userId, user) {
  if (!isAdmin(user)) {
    throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
  }

  const lead = await getLeadDocumentOrThrow(leadId);
  const targetUser = await validateAssignableUser(userId);

  lead.assignedTo = targetUser._id;
  await lead.save();

  await LeadActivity.create({
    lead: lead._id,
    user: user._id,
    activityType: LEAD_ACTIVITY_TYPES.OTHER,
    description: `Lead assigned to ${targetUser.name} (${targetUser.email})`,
  });

  return getLeadById(leadId);
}

/**
 * @param {string} leadId
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
async function archiveLead(leadId, user) {
  if (!isAdmin(user)) {
    throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
  }

  const lead = await getLeadDocumentOrThrow(leadId);

  if (!ACTIVE_LEAD_STATUSES.includes(lead.status)) {
    throw new AppError('Lead is already closed', 400, { code: 'LEAD_ALREADY_CLOSED' });
  }

  const previousStatus = lead.status;
  lead.status = LEAD_STATUSES.LOST;
  await lead.save();

  await LeadActivity.create({
    lead: lead._id,
    user: user._id,
    activityType: LEAD_ACTIVITY_TYPES.STATUS_CHANGED,
    description: `Status changed from ${previousStatus} to ${LEAD_STATUSES.LOST} (archived)`,
  });

  return getLeadById(leadId);
}

/**
 * @param {string} leadId
 * @param {string} noteText
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
async function addNote(leadId, noteText, user) {
  const lead = await getLeadDocumentOrThrow(leadId);
  assertCanManageLead(lead, user);

  const note = await LeadNote.create({
    lead: leadId,
    user: user._id,
    note: noteText,
  });

  const populated = await LeadNote.findById(note._id)
    .populate('user', USER_POPULATE_FIELDS)
    .lean();

  return toSafeNote(populated);
}

/**
 * @param {string} leadId
 */
async function listNotes(leadId) {
  await getLeadDocumentOrThrow(leadId);

  const notes = await LeadNote.find({ lead: leadId })
    .sort({ createdAt: 1 })
    .populate('user', USER_POPULATE_FIELDS)
    .lean();

  return notes.map(toSafeNote);
}

/**
 * @param {string} leadId
 * @param {{ activityType: string, description?: string }} data
 * @param {{ _id: import('mongoose').Types.ObjectId, role: string }} user
 */
async function addActivity(leadId, data, user) {
  const lead = await getLeadDocumentOrThrow(leadId);
  assertCanManageLead(lead, user);

  const activity = await LeadActivity.create({
    lead: leadId,
    user: user._id,
    activityType: data.activityType,
    description: data.description || '',
  });

  const populated = await LeadActivity.findById(activity._id)
    .populate('user', USER_POPULATE_FIELDS)
    .lean();

  return toSafeActivity(populated);
}

/**
 * @param {string} leadId
 */
async function listActivities(leadId) {
  await getLeadDocumentOrThrow(leadId);

  const activities = await LeadActivity.find({ lead: leadId })
    .sort({ createdAt: 1 })
    .populate('user', USER_POPULATE_FIELDS)
    .lean();

  return activities.map(toSafeActivity);
}

module.exports = {
  createLead,
  listLeads,
  getLeadById,
  updateLead,
  assignLead,
  archiveLead,
  addNote,
  listNotes,
  addActivity,
  listActivities,
  canManageLead,
};
