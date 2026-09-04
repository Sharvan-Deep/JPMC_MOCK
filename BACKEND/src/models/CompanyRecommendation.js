const mongoose = require('mongoose');
const { aiEvidenceSchema } = require('./aiEvidenceSchema');

const companyRecommendationSchema = new mongoose.Schema(
  {
    recommendation_id: {
      type: String,
      trim: true,
      index: true,
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
    recommended_action: {
      type: String,
      trim: true,
    },
    priority_level: {
      type: String,
      trim: true,
    },
    confidence: {
      type: mongoose.Schema.Types.Mixed,
    },
    reasons: {
      type: mongoose.Schema.Types.Mixed,
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
    evidence_sources: {
      type: [aiEvidenceSchema],
      default: [],
    },
    human_approval_required: {
      type: Boolean,
      default: true,
    },
    advisory_notice: {
      type: String,
      trim: true,
      default: '',
    },
    generated_at: {
      type: Date,
    },
    raw: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  {
    timestamps: true,
    collection: 'company_recommendations',
  }
);

companyRecommendationSchema.index({ companyId: 1, generated_at: -1 });

module.exports = mongoose.model('CompanyRecommendation', companyRecommendationSchema);
