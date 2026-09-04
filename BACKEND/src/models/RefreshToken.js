const mongoose = require('mongoose');

/**
 * Refresh-token session record.
 * Raw refresh tokens are never stored — only tokenHash.
 */
const refreshTokenSchema = new mongoose.Schema(
  {
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'User is required'],
      index: true,
    },
    tokenHash: {
      type: String,
      required: [true, 'Token hash is required'],
      unique: true,
    },
    expiresAt: {
      type: Date,
      required: [true, 'Expiry is required'],
    },
    revokedAt: {
      type: Date,
    },
  },
  {
    timestamps: true,
  }
);

refreshTokenSchema.index({ user: 1, createdAt: -1 });

// TTL cleanup for expired, non-revoked tokens.
refreshTokenSchema.index(
  { expiresAt: 1 },
  {
    expireAfterSeconds: 0,
    partialFilterExpression: { revokedAt: { $exists: false } },
  }
);

module.exports = mongoose.model('RefreshToken', refreshTokenSchema);
