const mongoose = require('mongoose');

/**
 * One-time password reset token record.
 * Raw reset tokens are never stored — only tokenHash.
 */
const passwordResetTokenSchema = new mongoose.Schema(
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
    usedAt: {
      type: Date,
    },
  },
  {
    timestamps: true,
  }
);

passwordResetTokenSchema.index({ user: 1, createdAt: -1 });

// TTL cleanup for unused expired tokens — application still validates expiry explicitly.
passwordResetTokenSchema.index(
  { expiresAt: 1 },
  {
    expireAfterSeconds: 0,
    partialFilterExpression: { usedAt: { $exists: false } },
  }
);

module.exports = mongoose.model('PasswordResetToken', passwordResetTokenSchema);
