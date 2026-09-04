const mongoose = require('mongoose');

/**
 * CSR policy document metadata (future ingestion — NOT part of the primary CSV).
 *
 * Relationship overview:
 *   CSRPolicy >── Company
 *
 * The MVP does not depend on this collection being populated.
 */
const csrPolicySchema = new mongoose.Schema(
  {
    company: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: [true, 'Company reference is required'],
    },
    financialYear: {
      type: String,
      trim: true,
    },
    title: {
      type: String,
      trim: true,
      maxlength: 500,
    },
    policyText: {
      type: String,
      default: '',
    },
    policyUrl: {
      type: String,
      trim: true,
    },
    source: {
      type: String,
      trim: true,
    },
    retrievedAt: {
      type: Date,
    },
  },
  {
    timestamps: true,
  }
);

csrPolicySchema.index({ company: 1, financialYear: 1 });
csrPolicySchema.index({ company: 1, createdAt: -1 });

module.exports = mongoose.model('CSRPolicy', csrPolicySchema);
