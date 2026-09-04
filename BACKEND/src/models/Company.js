const mongoose = require('mongoose');
const { buildCompanyNameKey } = require('../utils/dataNormalization');

/**
 * Company master record sourced from 03_company_ai_ready_summary.csv.
 *
 * Relationship overview:
 *   Company ──< Lead        (one company may have many leads over time)
 *   Company ──< CSRPolicy   (optional future CSR policy documents)
 *   Company ──< Source      (optional source/reference metadata)
 *
 * company_id is the MongoDB _id. company_name is indexed for search but is NOT
 * the primary identifier. companyNameKey (normalized name) is used for import
 * deduplication — see import service documentation for limitations.
 */
const companySchema = new mongoose.Schema(
  {
    company_name: {
      type: String,
      required: [true, 'Company name is required'],
      trim: true,
      maxlength: 500,
    },
    /**
     * Normalized lookup key: lowercase + trimmed company_name.
     * Used for idempotent CSV import matching. Not a business identifier.
     */
    companyNameKey: {
      type: String,
      required: true,
      unique: true,
      trim: true,
      lowercase: true,
    },
    wash_record_count: {
      type: Number,
      default: 0,
      min: 0,
    },
    financial_years: {
      type: [String],
      default: [],
    },
    states: {
      type: [String],
      default: [],
    },
    csr_sectors: {
      type: [String],
      default: [],
    },
    total_wash_spend_crore: {
      type: Number,
      default: 0,
      min: 0,
    },
    latest_financial_year: {
      type: String,
      trim: true,
    },
    total_water_spend_crore: {
      type: Number,
      default: 0,
      min: 0,
    },
    total_sanitation_spend_crore: {
      type: Number,
      default: 0,
      min: 0,
    },
    water_active_years: {
      type: [String],
      default: [],
    },
    sanitation_active_years: {
      type: [String],
      default: [],
    },
    wash_focus_evidence: {
      type: String,
      trim: true,
      default: '',
    },
    source: {
      type: String,
      trim: true,
      default: '',
    },
    source_retrieved_date: {
      type: Date,
    },
    /**
     * Structured AI analysis snapshot (classification/search/index results).
     * Algorithms live in the Python AI service; this is persistence only.
     */
    aiReadySummary: {
      type: mongoose.Schema.Types.Mixed,
    },
    leadScore: {
      type: mongoose.Schema.Types.Mixed,
    },
    freshness: {
      type: mongoose.Schema.Types.Mixed,
    },
    latestRecommendation: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  {
    timestamps: true,
  }
);

companySchema.pre('validate', function setCompanyNameKey(next) {
  if (this.company_name) {
    this.companyNameKey = buildCompanyNameKey(this.company_name);
  }
  next();
});

// Search and filter indexes
companySchema.index({ company_name: 1 });
companySchema.index({ company_name: 'text' });
companySchema.index({ latest_financial_year: 1 });
companySchema.index({ total_wash_spend_crore: -1 });
companySchema.index({ total_water_spend_crore: -1 });
companySchema.index({ total_sanitation_spend_crore: -1 });
companySchema.index({ wash_record_count: -1 });
companySchema.index({ states: 1 });
companySchema.index({ csr_sectors: 1 });
companySchema.index({ 'leadScore.total_score': -1 });

module.exports = mongoose.model('Company', companySchema);
