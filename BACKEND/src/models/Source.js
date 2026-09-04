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
    },
  },
  {
    timestamps: { createdAt: true, updatedAt: false },
  }
);

sourceSchema.index({ company: 1, createdAt: -1 });
sourceSchema.index({ sourceType: 1 });

module.exports = mongoose.model('Source', sourceSchema);
