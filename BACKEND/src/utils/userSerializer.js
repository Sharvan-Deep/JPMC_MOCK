/**
 * Return safe user fields for API responses.
 * Never exposes passwordHash or refresh-token data.
 *
 * @param {import('mongoose').Document | object} user
 * @returns {object | null}
 */
function toSafeUser(user) {
  if (!user) {
    return null;
  }

  const obj = user.toObject ? user.toObject() : user;

  return {
    id: obj._id,
    name: obj.name,
    email: obj.email,
    role: obj.role,
    isActive: obj.isActive,
    isEmailVerified: obj.isEmailVerified,
    lastLoginAt: obj.lastLoginAt,
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

module.exports = {
  toSafeUser,
};
