const mongoose = require('mongoose');
const { OUTREACH_DRAFT_STATUSES } = require('../config/constants');
const { aiEvidenceSchema } = require('./aiEvidenceSchema');

const outreachDraftSchema = new mongoose.Schema(
  {
    draft_id: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    companyId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: true,
    },
    leadId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Lead',
    },
    company: {
      type: String,
      trim: true,
      default: '',
    },
    subject: {
      type: String,
      trim: true,
      default: '',
    },
    body: {
      type: String,
      default: '',
    },
    subject_options: {
      type: mongoose.Schema.Types.Mixed,
    },
    personalization_points: {
      type: mongoose.Schema.Types.Mixed,
    },
    evidence_used: {
      type: [aiEvidenceSchema],
      default: [],
    },
    unsupported_claims: {
      type: mongoose.Schema.Types.Mixed,
    },
    warnings: {
      type: mongoose.Schema.Types.Mixed,
    },
    status: {
      type: String,
      enum: Object.values(OUTREACH_DRAFT_STATUSES),
      default: OUTREACH_DRAFT_STATUSES.DRAFT,
    },
    revision_history: {
      type: [mongoose.Schema.Types.Mixed],
      default: [],
    },
    validated_at: {
      type: Date,
    },
    approved_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
    },
    approved_at: {
      type: Date,
    },
    created_at: {
      type: Date,
    },
    updated_at: {
      type: Date,
    },
    raw: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  {
    timestamps: true,
    collection: 'outreach_drafts',
  }
);

outreachDraftSchema.index({ companyId: 1 });
outreachDraftSchema.index({ leadId: 1 });

module.exports = mongoose.model('OutreachDraft', outreachDraftSchema);
