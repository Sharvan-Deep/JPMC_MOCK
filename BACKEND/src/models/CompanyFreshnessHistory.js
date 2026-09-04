const mongoose = require('mongoose');
const { aiEvidenceSchema } = require('./aiEvidenceSchema');

const companyFreshnessHistorySchema = new mongoose.Schema(
  {
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
    status: {
      type: String,
      trim: true,
    },
    verification_cycle: {
      type: mongoose.Schema.Types.Mixed,
    },
    verified_at: {
      type: Date,
    },
    evidence: {
      type: [aiEvidenceSchema],
      default: [],
    },
    assessment: {
      type: mongoose.Schema.Types.Mixed,
    },
    changeVerification: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  {
    timestamps: true,
    collection: 'company_freshness_history',
  }
);

companyFreshnessHistorySchema.index({ companyId: 1, verified_at: -1 });

module.exports = mongoose.model('CompanyFreshnessHistory', companyFreshnessHistorySchema);
