const { Invitation, User } = require('../models');
const {
  INVITATION_STATUSES,
  DEFAULT_INVITATION_ROLE,
} = require('../config/constants');
const { AppError } = require('../utils/errors');
const { normalizeEmail } = require('../utils/email');
const {
  generateInvitationToken,
  hashInvitationToken,
} = require('../utils/tokenHash');
const { hashPassword } = require('../utils/password');
const {
  getInvitationExpiryDate,
  toPublicInvitation,
  markExpiredIfNeeded,
  isWithinResendCooldown,
} = require('../utils/invitationHelpers');
const { sendInvitationEmail } = require('./invitationEmailService');
const {
  validateInvitationCsvHeaders,
  parseInvitationCsvBuffer,
  validateName,
  validateEmailField,
} = require('../validators/invitationValidator');

/**
 * Find a pending invitation by raw token, with explicit expiry validation.
 * @param {string} rawToken
 * @returns {Promise<import('mongoose').Document | null>}
 */
async function findInvitationByToken(rawToken) {
  const tokenHash = hashInvitationToken(rawToken);
  const invitation = await Invitation.findOne({ tokenHash });

  if (!invitation) {
    return null;
  }

  await markExpiredIfNeeded(invitation);
  return invitation;
}

/**
 * @param {string} email
 */
async function findValidPendingInvitationByEmail(email) {
  const normalizedEmail = normalizeEmail(email);
  const invitation = await Invitation.findOne({
    email: normalizedEmail,
    status: INVITATION_STATUSES.PENDING,
  });

  if (!invitation) {
    return null;
  }

  await markExpiredIfNeeded(invitation);

  if (invitation.status !== INVITATION_STATUSES.PENDING) {
    return null;
  }

  return invitation;
}

/**
 * @param {string} email
 */
async function userExistsByEmail(email) {
  const normalizedEmail = normalizeEmail(email);
  const user = await User.findOne({ email: normalizedEmail }).select('_id');
  return Boolean(user);
}

/**
 * @param {{ name: string, email: string, invitedBy: string }} params
 * @param {{ skipCooldown?: boolean }} [options]
 */
async function createInvitation({ name, email, invitedBy }, options = {}) {
  const normalizedEmail = normalizeEmail(email);

  if (await userExistsByEmail(normalizedEmail)) {
    throw new AppError('A user with this email already exists', 409, {
      code: 'USER_EXISTS',
    });
  }

  const existingPending = await findValidPendingInvitationByEmail(normalizedEmail);
  if (existingPending) {
    if (!options.skipCooldown && isWithinResendCooldown(existingPending.updatedAt)) {
      throw new AppError(
        'A pending invitation for this email was sent recently. Please wait before inviting again.',
        429,
        { code: 'INVITE_COOLDOWN' }
      );
    }

    throw new AppError('A valid pending invitation already exists for this email', 409, {
      code: 'PENDING_INVITATION_EXISTS',
    });
  }

  const rawToken = generateInvitationToken();
  const tokenHash = hashInvitationToken(rawToken);

  const invitation = await Invitation.create({
    name: name.trim(),
    email: normalizedEmail,
    tokenHash,
    role: DEFAULT_INVITATION_ROLE,
    expiresAt: getInvitationExpiryDate(),
    status: INVITATION_STATUSES.PENDING,
    invitedBy,
  });

  const emailResult = await sendInvitationEmail({
    to: normalizedEmail,
    name: invitation.name,
    rawToken,
  });

  if (!emailResult.success) {
    await Invitation.findByIdAndDelete(invitation._id);
    throw new AppError('Failed to send invitation email', 502, {
      code: 'EMAIL_SEND_FAILED',
    });
  }

  return toPublicInvitation(invitation);
}

/**
 * @param {{ page?: number, limit?: number, status?: string, search?: string, sort?: string, order?: string }} query
 */
async function listInvitations(query = {}) {
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const skip = (page - 1) * limit;

  const filter = {};

  if (query.status) {
    filter.status = String(query.status).toUpperCase();
  }

  if (query.search) {
    const term = String(query.search).trim();
    const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
    filter.$or = [{ email: regex }, { name: regex }];
  }

  const sortField = ['createdAt', 'expiresAt', 'name', 'email', 'status'].includes(query.sort)
    ? query.sort
    : 'createdAt';
  const sortOrder = String(query.order || 'desc').toLowerCase() === 'asc' ? 1 : -1;

  const [items, total] = await Promise.all([
    Invitation.find(filter)
      .sort({ [sortField]: sortOrder })
      .skip(skip)
      .limit(limit)
      .populate('invitedBy', 'name email')
      .select('-tokenHash')
      .lean(),
    Invitation.countDocuments(filter),
  ]);

  return {
    items,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit) || 1,
    },
  };
}

/**
 * @param {string} invitationId
 */
async function getInvitationById(invitationId) {
  const invitation = await Invitation.findById(invitationId)
    .populate('invitedBy', 'name email')
    .select('-tokenHash');

  if (!invitation) {
    throw new AppError('Invitation not found', 404, { code: 'NOT_FOUND' });
  }

  return invitation;
}

/**
 * @param {string} invitationId
 */
async function resendInvitation(invitationId) {
  const invitation = await Invitation.findById(invitationId);

  if (!invitation) {
    throw new AppError('Invitation not found', 404, { code: 'NOT_FOUND' });
  }

  await markExpiredIfNeeded(invitation);

  if (invitation.status === INVITATION_STATUSES.ACCEPTED) {
    throw new AppError('Cannot resend an accepted invitation', 400, {
      code: 'INVITATION_ACCEPTED',
    });
  }

  if (invitation.status === INVITATION_STATUSES.REVOKED) {
    throw new AppError('Cannot resend a revoked invitation', 400, {
      code: 'INVITATION_REVOKED',
    });
  }

  if (isWithinResendCooldown(invitation.updatedAt)) {
    throw new AppError(
      'Invitation was sent recently. Please wait before resending.',
      429,
      { code: 'RESEND_COOLDOWN' }
    );
  }

  if (await userExistsByEmail(invitation.email)) {
    throw new AppError('A user with this email already exists', 409, {
      code: 'USER_EXISTS',
    });
  }

  const rawToken = generateInvitationToken();
  invitation.tokenHash = hashInvitationToken(rawToken);
  invitation.expiresAt = getInvitationExpiryDate();
  invitation.status = INVITATION_STATUSES.PENDING;
  await invitation.save();

  const emailResult = await sendInvitationEmail({
    to: invitation.email,
    name: invitation.name,
    rawToken,
  });

  if (!emailResult.success) {
    throw new AppError('Failed to send invitation email', 502, {
      code: 'EMAIL_SEND_FAILED',
    });
  }

  return toPublicInvitation(invitation);
}

/**
 * @param {string} invitationId
 */
async function revokeInvitation(invitationId) {
  const invitation = await Invitation.findById(invitationId);

  if (!invitation) {
    throw new AppError('Invitation not found', 404, { code: 'NOT_FOUND' });
  }

  if (invitation.status === INVITATION_STATUSES.ACCEPTED) {
    throw new AppError('Cannot revoke an accepted invitation', 400, {
      code: 'INVITATION_ACCEPTED',
    });
  }

  invitation.status = INVITATION_STATUSES.REVOKED;
  await invitation.save();

  return toPublicInvitation(invitation);
}

/**
 * @param {string} rawToken
 */
async function verifyInvitationToken(rawToken) {
  const invitation = await findInvitationByToken(rawToken);

  if (!invitation) {
    return {
      valid: false,
      name: null,
      email: null,
      role: null,
    };
  }

  if (invitation.status !== INVITATION_STATUSES.PENDING) {
    return {
      valid: false,
      name: invitation.name,
      email: invitation.email,
      role: invitation.role,
    };
  }

  if (invitation.expiresAt.getTime() <= Date.now()) {
    return {
      valid: false,
      name: invitation.name,
      email: invitation.email,
      role: invitation.role,
    };
  }

  return {
    valid: true,
    name: invitation.name,
    email: invitation.email,
    role: invitation.role,
  };
}

/**
 * @param {{ token: string, password: string, name?: string }} params
 */
async function activateAccount({ token, password, name }) {
  const invitation = await findInvitationByToken(token);

  if (!invitation) {
    throw new AppError('Invalid or expired invitation token', 400, {
      code: 'INVALID_TOKEN',
    });
  }

  if (invitation.status !== INVITATION_STATUSES.PENDING) {
    throw new AppError('Invitation is no longer valid', 400, {
      code: 'INVITATION_NOT_PENDING',
    });
  }

  if (invitation.expiresAt.getTime() <= Date.now()) {
    invitation.status = INVITATION_STATUSES.EXPIRED;
    await invitation.save();
    throw new AppError('Invitation has expired', 400, { code: 'INVITATION_EXPIRED' });
  }

  const normalizedEmail = invitation.email;

  if (await userExistsByEmail(normalizedEmail)) {
    throw new AppError('An account with this email already exists', 409, {
      code: 'USER_EXISTS',
    });
  }

  const passwordHash = await hashPassword(password);
  const displayName = name?.trim() || invitation.name;

  const user = await User.create({
    name: displayName,
    email: normalizedEmail,
    passwordHash,
    role: invitation.role,
    isActive: true,
    isEmailVerified: true,
  });

  invitation.status = INVITATION_STATUSES.ACCEPTED;
  invitation.acceptedAt = new Date();
  await invitation.save();

  return {
    user: {
      id: user._id,
      name: user.name,
      email: user.email,
      role: user.role,
      isActive: user.isActive,
      isEmailVerified: user.isEmailVerified,
    },
  };
}

/**
 * @param {Buffer} fileBuffer
 * @param {string} invitedBy
 */
async function importInvitationsFromCsv(fileBuffer, invitedBy) {
  const { rows, headers } = parseInvitationCsvBuffer(fileBuffer);
  const headerValidation = validateInvitationCsvHeaders(headers);

  if (!headerValidation.valid) {
    throw new AppError('Invalid CSV headers', 400, {
      code: 'INVALID_CSV_HEADERS',
      errors: [`Missing required columns: ${headerValidation.missing.join(', ')}`],
    });
  }

  const summary = {
    totalRows: rows.length,
    invited: 0,
    skipped: 0,
    failed: 0,
    errors: [],
  };

  const seenEmails = new Set();

  for (let index = 0; index < rows.length; index += 1) {
    const rowNumber = index + 2;
    const row = rows[index];

    const get = (field) => {
      const key = Object.keys(row).find((k) => k.trim().toLowerCase() === field);
      return key ? row[key] : '';
    };

    const name = String(get('name') || '').trim();
    const emailRaw = String(get('email') || '').trim();

    const nameResult = validateName(name);
    const emailResult = validateEmailField(emailRaw);

    if (!nameResult.valid || !emailResult.valid) {
      summary.failed += 1;
      summary.errors.push({
        row: rowNumber,
        email: emailRaw || null,
        message: [...nameResult.errors, ...emailResult.errors].join('; '),
      });
      continue;
    }

    const email = emailResult.normalized;

    if (seenEmails.has(email)) {
      summary.skipped += 1;
      summary.errors.push({
        row: rowNumber,
        email,
        message: 'Duplicate email within CSV file',
      });
      continue;
    }

    seenEmails.add(email);

    try {
      if (await userExistsByEmail(email)) {
        summary.skipped += 1;
        summary.errors.push({
          row: rowNumber,
          email,
          message: 'User already exists',
        });
        continue;
      }

      const existingPending = await findValidPendingInvitationByEmail(email);
      if (existingPending) {
        summary.skipped += 1;
        summary.errors.push({
          row: rowNumber,
          email,
          message: 'Valid pending invitation already exists',
        });
        continue;
      }

      await createInvitation({ name, email, invitedBy }, { skipCooldown: true });
      summary.invited += 1;
    } catch (err) {
      summary.failed += 1;
      summary.errors.push({
        row: rowNumber,
        email,
        message: err instanceof AppError ? err.message : 'Failed to create invitation',
      });
    }
  }

  return summary;
}

module.exports = {
  createInvitation,
  listInvitations,
  getInvitationById,
  resendInvitation,
  revokeInvitation,
  verifyInvitationToken,
  activateAccount,
  importInvitationsFromCsv,
  findInvitationByToken,
};
