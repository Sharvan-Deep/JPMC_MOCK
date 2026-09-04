const outreachService = require('../services/outreachService');
const { AppError } = require('../utils/errors');
const {
  validateOutreachEditBody,
  validateOutreachApproveBody,
  validateOutreachSendBody,
  validateDraftIdParam,
} = require('../validators/aiIntegrationValidator');

function draftId(req) {
  const validation = validateDraftIdParam(req.params.id);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  return validation.value;
}

async function editDraft(req, res) {
  const validation = validateOutreachEditBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await outreachService.editOutreach(draftId(req), req.user, validation.data);

  res.json({
    success: true,
    data,
  });
}

async function getDraft(req, res) {
  const data = await outreachService.getOutreach(draftId(req), req.user);

  res.json({
    success: true,
    data,
  });
}

async function validateDraft(req, res) {
  const data = await outreachService.validateOutreach(draftId(req), req.user);

  res.json({
    success: true,
    data,
  });
}

async function approveDraft(req, res) {
  const validation = validateOutreachApproveBody(req.body || {});

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await outreachService.approveOutreach(draftId(req), req.user, validation.data);

  res.json({
    success: true,
    data,
  });
}

async function sendDraft(req, res) {
  const validation = validateOutreachSendBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await outreachService.sendOutreach(draftId(req), req.user, validation.data);

  res.json({
    success: true,
    data,
  });
}

module.exports = {
  editDraft,
  getDraft,
  validateDraft,
  approveDraft,
  sendDraft,
};
