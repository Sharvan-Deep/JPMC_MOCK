const { User } = require('../models');
const { AppError } = require('../utils/errors');
const { toSafeUser } = require('../utils/userSerializer');
const { USER_ROLES } = require('../config/constants');

const SAFE_USER_SELECT =
  'name email role isActive isEmailVerified lastLoginAt createdAt updatedAt';

/**
 * @param {string} userId
 */
async function getUserDocumentOrThrow(userId) {
  const user = await User.findById(userId).select(SAFE_USER_SELECT);

  if (!user) {
    throw new AppError('User not found', 404, { code: 'USER_NOT_FOUND' });
  }

  return user;
}

/**
 * @param {string | null | undefined} excludeUserId
 */
async function countActiveAdmins(excludeUserId = null) {
  const filter = {
    role: USER_ROLES.ADMIN,
    isActive: true,
  };

  if (excludeUserId) {
    filter._id = { $ne: excludeUserId };
  }

  return User.countDocuments(filter);
}

/**
 * @param {import('mongoose').Document} targetUser
 * @param {string} actingUserId
 */
function assertNotSelf(actingUserId, targetUserId, actionMessage) {
  if (actingUserId === targetUserId.toString()) {
    throw new AppError(actionMessage, 400, { code: 'SELF_MODIFICATION_FORBIDDEN' });
  }
}

/**
 * @param {import('mongoose').Document} targetUser
 */
async function assertAdminRemainsAvailable(targetUser) {
  if (targetUser.role !== USER_ROLES.ADMIN || !targetUser.isActive) {
    return;
  }

  const otherActiveAdmins = await countActiveAdmins(targetUser._id);

  if (otherActiveAdmins === 0) {
    throw new AppError('Cannot remove the last active administrator', 400, {
      code: 'LAST_ADMIN_PROTECTED',
    });
  }
}

/**
 * @param {Record<string, unknown>} query
 */
async function listUsers(query) {
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const skip = (page - 1) * limit;
  const filter = {};

  if (query.role) {
    filter.role = query.role;
  }

  if (query.isActive !== undefined) {
    filter.isActive = query.isActive;
  }

  if (query.search) {
    const term = String(query.search).trim();
    const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
    filter.$or = [{ name: regex }, { email: regex }];
  }

  const sortField = [
    'name',
    'email',
    'role',
    'isActive',
    'createdAt',
    'updatedAt',
    'lastLoginAt',
  ].includes(query.sort)
    ? query.sort
    : 'createdAt';
  const sortOrder = String(query.order || 'desc').toLowerCase() === 'asc' ? 1 : -1;

  const [users, total] = await Promise.all([
    User.find(filter)
      .select(SAFE_USER_SELECT)
      .sort({ [sortField]: sortOrder })
      .skip(skip)
      .limit(limit)
      .lean(),
    User.countDocuments(filter),
  ]);

  return {
    users: users.map(toSafeUser),
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit) || 0,
    },
  };
}

/**
 * @param {string} userId
 */
async function getUserById(userId) {
  const user = await getUserDocumentOrThrow(userId);
  return toSafeUser(user);
}

/**
 * @param {string} userId
 * @param {{ name: string }} data
 */
async function updateUserProfile(userId, data) {
  const user = await getUserDocumentOrThrow(userId);
  user.name = data.name;
  await user.save();

  return toSafeUser(user);
}

/**
 * @param {string} userId
 * @param {string} role
 * @param {string} actingUserId
 */
async function updateUserRole(userId, role, actingUserId) {
  const user = await getUserDocumentOrThrow(userId);

  if (actingUserId === userId && user.role === USER_ROLES.ADMIN && role !== USER_ROLES.ADMIN) {
    throw new AppError('Administrators cannot change their own role', 400, {
      code: 'SELF_DEMOTION_FORBIDDEN',
    });
  }

  if (user.role === USER_ROLES.ADMIN && role !== USER_ROLES.ADMIN) {
    await assertAdminRemainsAvailable(user);
  }

  user.role = role;
  await user.save();

  return toSafeUser(user);
}

/**
 * @param {string} userId
 * @param {boolean} isActive
 * @param {string} actingUserId
 */
async function updateUserStatus(userId, isActive, actingUserId) {
  const user = await getUserDocumentOrThrow(userId);

  if (!isActive) {
    assertNotSelf(
      actingUserId,
      user._id,
      'Administrators cannot deactivate their own account'
    );

    if (user.role === USER_ROLES.ADMIN && user.isActive) {
      await assertAdminRemainsAvailable(user);
    }
  }

  user.isActive = isActive;
  await user.save();

  return toSafeUser(user);
}

module.exports = {
  listUsers,
  getUserById,
  updateUserProfile,
  updateUserRole,
  updateUserStatus,
};
