const mongoose = require('mongoose');

/**
 * Historical CSR spend row imported from the detailed CSR CSV.
 *
 * Relationship overview:
 *   CSRActivity >── Company
 *
 * company_name is never the primary key. Matching to Company uses companyNameKey
 * at import time; the stored identity is the Company ObjectId.
 *
 * uniquenessKey is a deterministic fingerprint of the imported row so re-running
 * the importer upserts instead of duplicating records. The CSV has no project ID.
 */
const csrActivitySchema = new mongoose.Schema(
  {
    company: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: [true, 'Company reference is required'],
    },
    financialYear: {
      type: String,
      trim: true,
      default: '',
    },
    psuStatus: {
      type: String,
      trim: true,
      default: '',
      maxlength: 50,
    },
    state: {
      type: String,
      trim: true,
      default: '',
      maxlength: 200,
    },
    developmentSector: {
      type: String,
      trim: true,
      default: '',
      maxlength: 300,
    },
    subDevelopmentSector: {
      type: String,
      trim: true,
      default: '',
      maxlength: 300,
    },
    amountSpentCrore: {
      type: Number,
      default: 0,
      min: 0,
    },
    uniquenessKey: {
      type: String,
      required: true,
      unique: true,
    },
    sourceName: {
      type: String,
      trim: true,
      default: '',
      maxlength: 300,
    },
  },
  {
    timestamps: true,
  }
);

csrActivitySchema.index({ company: 1, financialYear: 1 });
csrActivitySchema.index({ company: 1, createdAt: -1 });
csrActivitySchema.index({ state: 1 });
csrActivitySchema.index({ developmentSector: 1 });

module.exports = mongoose.model('CSRActivity', csrActivitySchema);
