const mongoose = require('mongoose');
const { LEAD_STATUSES, LEAD_PRIORITIES, ACTIVE_LEAD_STATUSES } = require('../config/constants');

/**
 * Donor lead — a Company flagged for fundraising outreach.
 *
 * Relationship overview:
 *   Lead >── Company      (required)
 *   Lead >── User         assignedTo
 *   Lead >── User         createdBy
 *   Lead ──< LeadNote
 *   Lead ──< LeadActivity
 *
 * Priority is set manually or by an external system — NOT calculated by this backend.
 */
const leadSchema = new mongoose.Schema(
  {
    company: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: [true, 'Company reference is required'],
    },
    assignedTo: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'Assigned user is required'],
    },
    status: {
      type: String,
      enum: {
        values: Object.values(LEAD_STATUSES),
        message: '{VALUE} is not a valid lead status',
      },
      default: LEAD_STATUSES.NEW,
    },
    priority: {
      type: String,
      enum: {
        values: Object.values(LEAD_PRIORITIES),
        message: '{VALUE} is not a valid lead priority',
      },
      default: LEAD_PRIORITIES.MEDIUM,
    },
    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'Creator reference is required'],
    },
  },
  {
    timestamps: true,
  }
);

leadSchema.index({ status: 1 });
leadSchema.index({ priority: 1 });
leadSchema.index({ assignedTo: 1 });
leadSchema.index({ company: 1 });
leadSchema.index({ createdBy: 1 });
leadSchema.index({ assignedTo: 1, status: 1 });

/**
 * Prevent more than one active (non-terminal) lead per company.
 * A company may have many leads over time (e.g. after WON/LOST), but only one
 * open lead at a time.
 */
leadSchema.index(
  { company: 1 },
  {
    unique: true,
    partialFilterExpression: {
      status: { $in: ACTIVE_LEAD_STATUSES },
    },
    name: 'unique_active_lead_per_company',
  }
);

module.exports = mongoose.model('Lead', leadSchema);
