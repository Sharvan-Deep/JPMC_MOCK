const mongoose = require('mongoose');

/**
 * External source/reference metadata for a company (future ingestion).
 *
 * Relationship overview:
 *   Source >── Company
 *
 * Separate from the primary company CSV summary data.
 */
const sourceSchema = new mongoose.Schema(
  {
    company: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Company',
      required: [true, 'Company reference is required'],
    },
    sourceType: {
      type: String,
      trim: true,
      maxlength: 100,
    },
    sourceName: {
      type: String,
      trim: true,
      maxlength: 300,
    },
    sourceUrl: {
      type: String,
      trim: true,
    },
    retrievedAt: {
      type: Date,
      default: Date.now,
    },
    // Document retrieval and versioning storage fields
    documentType: {
      type: String,
      enum: ['annual_report', 'csr_policy', 'brsr', 'disclosure'],
      trim: true,
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
    sha256: {
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
    publishedDate: {
      type: Date,
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
    timestamps: { createdAt: true, updatedAt: true },
  }
);

sourceSchema.index({ company: 1, createdAt: -1 });
sourceSchema.index({ sourceType: 1 });
sourceSchema.index({ company: 1, documentType: 1, financialYear: 1, version: -1 });
sourceSchema.index({ sha256: 1 });

module.exports = mongoose.model('Source', sourceSchema);
