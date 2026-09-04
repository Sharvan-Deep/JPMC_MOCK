const mongoose = require('mongoose');
const { aiEvidenceSchema } = require('./aiEvidenceSchema');

const companyLeadScoreSchema = new mongoose.Schema(
  {
    companyId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: true,
    },
    total_score: {
      type: Number,
    },
    priority_band: {
      type: String,
      trim: true,
    },
    components: {
      type: mongoose.Schema.Types.Mixed,
    },
    scoring_version: {
      type: String,
      trim: true,
    },
    scored_at: {
      type: Date,
    },
    positive_factors: {
      type: [String],
      default: [],
    },
    limiting_factors: {
      type: [String],
      default: [],
    },
    missing_information: {
      type: [String],
      default: [],
    },
    evidence_coverage: {
      type: mongoose.Schema.Types.Mixed,
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
    collection: 'company_lead_scores',
  }
);

companyLeadScoreSchema.index({ companyId: 1, scored_at: -1 });

module.exports = mongoose.model('CompanyLeadScore', companyLeadScoreSchema);
