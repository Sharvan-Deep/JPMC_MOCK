const mongoose = require('mongoose');
const {
  USER_ROLES,
  INVITATION_STATUSES,
  DEFAULT_INVITATION_ROLE,
} = require('../config/constants');

/**
 * Admin-provisioned user invitation.
 * Raw invitation tokens are never stored — only tokenHash.
 */
const invitationSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'Name is required'],
      trim: true,
      maxlength: 150,
    },
    email: {
      type: String,
      required: [true, 'Email is required'],
      lowercase: true,
      trim: true,
      maxlength: 255,
      index: true,
    },
    tokenHash: {
      type: String,
      required: [true, 'Token hash is required'],
      unique: true,
    },
    role: {
      type: String,
      enum: {
        values: Object.values(USER_ROLES),
        message: '{VALUE} is not a valid role',
      },
      default: DEFAULT_INVITATION_ROLE,
      required: true,
    },
    expiresAt: {
      type: Date,
      required: [true, 'Expiry is required'],
    },
    status: {
      type: String,
      enum: {
        values: Object.values(INVITATION_STATUSES),
        message: '{VALUE} is not a valid invitation status',
      },
      default: INVITATION_STATUSES.PENDING,
      required: true,
      index: true,
    },
    invitedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'Invited by is required'],
      index: true,
    },
    acceptedAt: {
      type: Date,
    },
  },
  {
    timestamps: true,
  }
);

invitationSchema.index({ email: 1, status: 1 });
invitationSchema.index({ status: 1, createdAt: -1 });
invitationSchema.index({ createdAt: -1 });

// TTL cleanup for pending invitations only — application still validates expiry explicitly.
invitationSchema.index(
  { expiresAt: 1 },
  {
    expireAfterSeconds: 0,
    partialFilterExpression: { status: INVITATION_STATUSES.PENDING },
  }
);

module.exports = mongoose.model('Invitation', invitationSchema);
