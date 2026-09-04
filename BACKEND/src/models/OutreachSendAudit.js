const mongoose = require('mongoose');
const { aiEvidenceSchema } = require('./aiEvidenceSchema');

const outreachSendAuditSchema = new mongoose.Schema(
  {
    send_id: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    draft_id: {
      type: String,
      trim: true,
    },
    companyId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: true,
    },
    company: {
      type: String,
      trim: true,
      default: '',
    },
    recipient_email: {
      type: String,
      trim: true,
      lowercase: true,
    },
    subject: {
      type: String,
      trim: true,
      default: '',
    },
    body_preview: {
      type: String,
      default: '',
    },
    approved_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
    },
    sent_at: {
      type: Date,
    },
    status: {
      type: String,
      trim: true,
    },
    error_message: {
      type: String,
      trim: true,
      default: '',
    },
    evidence: {
      type: [aiEvidenceSchema],
      default: [],
    },
    raw: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  {
    timestamps: true,
    collection: 'outreach_send_audits',
  }
);

outreachSendAuditSchema.index({ companyId: 1 });

module.exports = mongoose.model('OutreachSendAudit', outreachSendAuditSchema);
