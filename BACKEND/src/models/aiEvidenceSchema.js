const mongoose = require('mongoose');

/**
 * AI evidence reference — stored only when the AI service returns these fields.
 * Do not invent unsupported evidence.
 */
const aiEvidenceSchema = new mongoose.Schema(
  {
    company: { type: String, trim: true },
    financial_year: { type: String, trim: true },
    document_type: { type: String, trim: true },
    document_version: { type: String, trim: true },
    page: { type: mongoose.Schema.Types.Mixed },
    source_url: { type: String, trim: true },
    relevant_source_text: { type: String, trim: true },
    document_hash: { type: String, trim: true },
  },
  { _id: false }
);

module.exports = {
  aiEvidenceSchema,
};
