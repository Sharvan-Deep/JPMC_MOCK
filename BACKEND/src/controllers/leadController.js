const leadService = require('../services/leadService');
const { AppError } = require('../utils/errors');
const {
  validateCreateLeadBody,
  validateUpdateLeadBody,
  validateAssignLeadBody,
  validateCreateNoteBody,
  validateCreateActivityBody,
  validateListLeadsQuery,
} = require('../validators/leadValidator');

async function createLead(req, res) {
  const validation = validateCreateLeadBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await leadService.createLead(validation.data, req.user);

  res.status(201).json({
    success: true,
    data,
  });
}

async function listLeads(req, res) {
  const validation = validateListLeadsQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const result = await leadService.listLeads(validation.data);

  res.json({
    success: true,
    data: result,
  });
}

async function getLead(req, res) {
  const data = await leadService.getLeadById(req.params.leadId);

  res.json({
    success: true,
    data,
  });
}

async function updateLead(req, res) {
  const validation = validateUpdateLeadBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await leadService.updateLead(
    req.params.leadId,
    validation.data,
    req.user
  );

  res.json({
    success: true,
    data,
  });
}

async function assignLead(req, res) {
  const validation = validateAssignLeadBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await leadService.assignLead(
    req.params.leadId,
    validation.data.userId,
    req.user
  );

  res.json({
    success: true,
    data,
  });
}

async function archiveLead(req, res) {
  const data = await leadService.archiveLead(req.params.leadId, req.user);

  res.json({
    success: true,
    message: 'Lead archived',
    data,
  });
}

async function addNote(req, res) {
  const validation = validateCreateNoteBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const note = await leadService.addNote(
    req.params.leadId,
    validation.data.note,
    req.user
  );

  res.status(201).json({
    success: true,
    data: { note },
  });
}

async function listNotes(req, res) {
  const notes = await leadService.listNotes(req.params.leadId);

  res.json({
    success: true,
    data: { notes },
  });
}

async function addActivity(req, res) {
  const validation = validateCreateActivityBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const activity = await leadService.addActivity(
    req.params.leadId,
    validation.data,
    req.user
  );

  res.status(201).json({
    success: true,
    data: { activity },
  });
}

async function listActivities(req, res) {
  const activities = await leadService.listActivities(req.params.leadId);

  res.json({
    success: true,
    data: { activities },
  });
}

module.exports = {
  createLead,
  listLeads,
  getLead,
  updateLead,
  assignLead,
  archiveLead,
  addNote,
  listNotes,
  addActivity,
  listActivities,
};
