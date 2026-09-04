const mongoose = require('mongoose');
const { LEAD_ACTIVITY_TYPES } = require('../config/constants');

/**
 * Outreach / follow-up activity log for a donor lead.
 * Immutable after creation (no updatedAt).
 *
 * Relationship overview:
 *   LeadActivity >── Lead
 *   LeadActivity >── User
 */
const leadActivitySchema = new mongoose.Schema(
  {
    lead: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Lead',
      required: [true, 'Lead reference is required'],
    },
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'User reference is required'],
    },
    activityType: {
      type: String,
      enum: {
        values: Object.values(LEAD_ACTIVITY_TYPES),
        message: '{VALUE} is not a valid activity type',
      },
      required: [true, 'Activity type is required'],
    },
    description: {
      type: String,
      trim: true,
      maxlength: 2000,
      default: '',
    },
  },
  {
    timestamps: { createdAt: true, updatedAt: false },
  }
);

leadActivitySchema.index({ lead: 1, createdAt: -1 });
leadActivitySchema.index({ user: 1 });
leadActivitySchema.index({ activityType: 1 });

module.exports = mongoose.model('LeadActivity', leadActivitySchema);
