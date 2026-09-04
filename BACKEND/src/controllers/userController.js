const userService = require('../services/userService');
const { AppError } = require('../utils/errors');
const {
  validateListUsersQuery,
  validateUpdateUserBody,
  validateRoleBody,
  validateStatusBody,
} = require('../validators/userValidator');

async function listUsers(req, res) {
  const validation = validateListUsersQuery(req.query);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const data = await userService.listUsers(validation.data);

  res.json({
    success: true,
    data,
  });
}

async function getUser(req, res) {
  const user = await userService.getUserById(req.params.userId);

  res.json({
    success: true,
    data: { user },
  });
}

async function updateUser(req, res) {
  const validation = validateUpdateUserBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const user = await userService.updateUserProfile(req.params.userId, validation.data);

  res.json({
    success: true,
    data: { user },
  });
}

async function updateRole(req, res) {
  const validation = validateRoleBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const user = await userService.updateUserRole(
    req.params.userId,
    validation.data.role,
    req.user.id
  );

  res.json({
    success: true,
    data: { user },
  });
}

async function updateStatus(req, res) {
  const validation = validateStatusBody(req.body);

  if (!validation.valid) {
    throw new AppError('Validation failed', 400, { errors: validation.errors });
  }

  const user = await userService.updateUserStatus(
    req.params.userId,
    validation.data.isActive,
    req.user.id
  );

  res.json({
    success: true,
    data: { user },
  });
}

module.exports = {
  listUsers,
  getUser,
  updateUser,
  updateRole,
  updateStatus,
};
