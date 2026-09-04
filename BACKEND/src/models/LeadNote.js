const mongoose = require('mongoose');

/**
 * Free-text note attached to a donor lead.
 *
 * Relationship overview:
 *   LeadNote >── Lead
 *   LeadNote >── User
 */
const leadNoteSchema = new mongoose.Schema(
  {
    lead: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Lead',
      required: [true, 'Lead reference is required'],
    },
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'User reference is required'],
    },
    note: {
      type: String,
      required: [true, 'Note content is required'],
      trim: true,
      maxlength: 5000,
    },
  },
  {
    timestamps: true,
  }
);

leadNoteSchema.index({ lead: 1, createdAt: -1 });
leadNoteSchema.index({ user: 1 });

module.exports = mongoose.model('LeadNote', leadNoteSchema);
