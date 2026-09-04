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
      default: Date.now,
    },
    sha256: {
      type: String,
      trim: true,
    },
    localFilePath: {
      type: String,
      trim: true,
    },
    fileName: {
      type: String,
      trim: true,
    },
    fileSize: {
      type: Number,
      min: 0,
    },
    contentType: {
      type: String,
      trim: true,
    },
    version: {
      type: Number,
      default: 1,
      min: 1,
    },
    isLatest: {
      type: Boolean,
      default: true,
    },
    status: {
      type: String,
      enum: ['FOUND', 'NOT_FOUND', 'ERROR'],
      default: 'FOUND',
    },
    errorInformation: {
      type: String,
      trim: true,
    },
  },
  {
    timestamps: true,
  }
);

csrPolicySchema.index({ company: 1, financialYear: 1, version: -1 });
csrPolicySchema.index({ company: 1, createdAt: -1 });
csrPolicySchema.index({ sha256: 1 });

module.exports = mongoose.model('CSRPolicy', csrPolicySchema);
