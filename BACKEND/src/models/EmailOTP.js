const mongoose = require('mongoose');

/**
 * Temporary email OTP verification record.
 * Raw OTP values are never stored — only a hash.
 * Documents auto-expire via TTL index on expiresAt.
 */
const emailOTPSchema = new mongoose.Schema(
  {
    email: {
      type: String,
      required: [true, 'Email is required'],
      lowercase: true,
      trim: true,
      index: true,
    },
    otpHash: {
      type: String,
      required: [true, 'OTP hash is required'],
    },
    expiresAt: {
      type: Date,
      required: [true, 'Expiry is required'],
    },
    attempts: {
      type: Number,
      default: 0,
      min: 0,
    },
    verified: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: { createdAt: true, updatedAt: false },
  }
);

// TTL index — MongoDB removes documents once expiresAt is reached
emailOTPSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

// Rate-limit friendly lookup: most recent OTP per email
emailOTPSchema.index({ email: 1, createdAt: -1 });

module.exports = mongoose.model('EmailOTP', emailOTPSchema);
