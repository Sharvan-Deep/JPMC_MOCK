const invitationService = require('../services/invitationService');
const { AppError } = require('../utils/errors');
const {
  validateCreateInvitationBody,
  validateTokenBody,
  validateActivationBody,
} = require('../validators/invitationValidator');

async function createInvitation(req, res) {
  const validation = validateCreateInvitationBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const invitation = await invitationService.createInvitation({
    ...validation.data,
    invitedBy: req.user._id,
  });

  res.status(201).json({
    success: true,
    message: 'Invitation created and email sent',
    data: invitation,
  });
}

async function listInvitations(req, res) {
  const result = await invitationService.listInvitations(req.query);

  res.json({
    success: true,
    data: result.items,
    pagination: result.pagination,
  });
}

async function getInvitation(req, res) {
  const invitation = await invitationService.getInvitationById(req.params.invitationId);

  res.json({
    success: true,
    data: invitation,
  });
}

async function resendInvitation(req, res) {
  const invitation = await invitationService.resendInvitation(req.params.invitationId);

  res.json({
    success: true,
    message: 'Invitation resent',
    data: invitation,
  });
}

async function revokeInvitation(req, res) {
  const invitation = await invitationService.revokeInvitation(req.params.invitationId);

  res.json({
    success: true,
    message: 'Invitation revoked',
    data: invitation,
  });
}

async function verifyInvitation(req, res) {
  const validation = validateTokenBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const result = await invitationService.verifyInvitationToken(validation.token);

  res.json({
    success: true,
    data: result,
  });
}

async function activateAccount(req, res) {
  const validation = validateActivationBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const result = await invitationService.activateAccount(validation.data);

  res.status(201).json({
    success: true,
    message: 'Account activated successfully',
    data: result,
  });
}

async function importInvitations(req, res) {
  if (!req.file || !req.file.buffer) {
    throw new AppError('CSV file is required', 400, { code: 'FILE_REQUIRED' });
  }

  const summary = await invitationService.importInvitationsFromCsv(
    req.file.buffer,
    req.user._id
  );

  res.status(200).json({
    success: true,
    data: summary,
  });
}

module.exports = {
  createInvitation,
  listInvitations,
  getInvitation,
  resendInvitation,
  revokeInvitation,
  verifyInvitation,
  activateAccount,
  importInvitations,
};
