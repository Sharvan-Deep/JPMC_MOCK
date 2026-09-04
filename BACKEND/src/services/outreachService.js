const crypto = require('crypto');
const { OutreachDraft, OutreachSendAudit, Lead } = require('../models');
const aiService = require('./aiService');
const { loadCompanyAiContext, buildCanonicalCompanyPayload } = require('./aiContextService');
const { getManagedLead } = require('./leadScoringService');
const leadService = require('./leadService');
const { extractEvidence, firstDefined } = require('../utils/aiEvidence');
const { AppError } = require('../utils/errors');
const { OUTREACH_DRAFT_STATUSES, USER_ROLES } = require('../config/constants');

function bodyPreview(body) {
  const text = String(body || '');
  return text.length > 280 ? `${text.slice(0, 277)}...` : text;
}

function mapDraftFromAi(aiDraft, extras = {}) {
  return {
    draft_id: firstDefined(aiDraft?.draft_id, aiDraft?.draftId, aiDraft?.id, extras.draft_id),
    subject: firstDefined(aiDraft?.subject, extras.subject, ''),
    body: firstDefined(aiDraft?.body, extras.body, ''),
    subject_options: firstDefined(aiDraft?.subject_options, aiDraft?.subjectOptions),
    personalization_points: firstDefined(
      aiDraft?.personalization_points,
      aiDraft?.personalizationPoints
    ),
    evidence_used: extractEvidence(aiDraft),
    unsupported_claims: firstDefined(aiDraft?.unsupported_claims, aiDraft?.unsupportedClaims),
    warnings: firstDefined(aiDraft?.warnings, extras.warnings),
    created_at: firstDefined(aiDraft?.created_at, aiDraft?.createdAt),
    updated_at: firstDefined(aiDraft?.updated_at, aiDraft?.updatedAt, new Date()),
    raw: aiDraft,
  };
}

async function assertCanAccessDraft(draft, user) {
  if (user.role === USER_ROLES.ADMIN) {
    return;
  }

  if (draft.leadId) {
    const lead = await Lead.findById(draft.leadId);
    if (lead && leadService.canManageLead(lead, user)) {
      return;
    }
  }

  throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
}

async function getDraftOrThrow(draftId) {
  const draft = await OutreachDraft.findOne({ draft_id: draftId });

  if (!draft) {
    throw new AppError('Outreach draft not found', 404, { code: 'DRAFT_NOT_FOUND' });
  }

  return draft;
}

async function upsertDraft(company, lead, aiDraft, extras = {}) {
  const mapped = mapDraftFromAi(aiDraft, extras);

  if (!mapped.draft_id) {
    mapped.draft_id = `local-${crypto.randomUUID()}`;
  }

  const existing = await OutreachDraft.findOne({ draft_id: mapped.draft_id });
  const nextStatus = extras.status || existing?.status || OUTREACH_DRAFT_STATUSES.DRAFT;

  if (existing) {
    existing.subject = mapped.subject;
    existing.body = mapped.body;
    existing.subject_options = mapped.subject_options;
    existing.personalization_points = mapped.personalization_points;
    existing.evidence_used = mapped.evidence_used;
    existing.unsupported_claims = mapped.unsupported_claims;
    existing.warnings = mapped.warnings;
    existing.status = nextStatus;
    existing.updated_at = mapped.updated_at;
    existing.raw = mapped.raw;

    if (extras.revision) {
      existing.revision_history = [...(existing.revision_history || []), extras.revision];
    }

    if (extras.approved_by) {
      existing.approved_by = extras.approved_by;
      existing.approved_at = extras.approved_at || new Date();
    }

    if (extras.validated_at) {
      existing.validated_at = extras.validated_at;
    }

    await existing.save();
    return existing;
  }

  return OutreachDraft.create({
    ...mapped,
    companyId: company._id,
    leadId: lead?._id,
    company: company.company_name,
    status: nextStatus,
    revision_history: extras.revision ? [extras.revision] : [],
    approved_by: extras.approved_by,
    approved_at: extras.approved_at,
    validated_at: extras.validated_at,
    created_at: mapped.created_at || new Date(),
  });
}

async function generateOutreach(leadId, user, body = {}) {
  const lead = await getManagedLead(leadId, user);
  const context = await loadCompanyAiContext(lead.company.toString());
  const canonical = buildCanonicalCompanyPayload(context);

  const aiDraft = await aiService.draftOutreach({
    company_id: canonical.company_id,
    company: canonical.company,
    recipient_role: body.recipientRole,
    tone: body.tone,
    recommendation: context.company.latestRecommendation || null,
    score: canonical.lead_score,
    freshness: canonical.freshness,
    ...canonical,
    human_approval_required: true,
  });

  const draft = await upsertDraft(context.company, lead, aiDraft, {
    status: OUTREACH_DRAFT_STATUSES.DRAFT,
  });

  return {
    draft: draft.toObject(),
    warnings: draft.warnings || aiDraft?.warnings || [],
    human_approval_required: true,
  };
}

async function editOutreach(draftId, user, body) {
  const draft = await getDraftOrThrow(draftId);
  await assertCanAccessDraft(draft, user);

  const revision = {
    at: new Date(),
    userId: user._id,
    subject: draft.subject,
    body: draft.body,
  };

  const aiDraft = await aiService.editOutreach({
    draft_id: draft.draft_id,
    subject: body.subject,
    body: body.body,
    instruction: body.instruction,
    tone: body.tone,
  });

  const updated = await upsertDraft(
    { _id: draft.companyId, company_name: draft.company },
    draft.leadId ? { _id: draft.leadId } : null,
    aiDraft,
    {
      status: OUTREACH_DRAFT_STATUSES.DRAFT,
      revision,
      subject: body.subject,
      body: body.body,
    }
  );

  return { draft: updated.toObject(), warnings: updated.warnings || aiDraft?.warnings || [] };
}

async function getOutreach(draftId, user) {
  const draft = await getDraftOrThrow(draftId);
  await assertCanAccessDraft(draft, user);

  return { draft: draft.toObject() };
}

async function validateOutreach(draftId, user) {
  const draft = await getDraftOrThrow(draftId);
  await assertCanAccessDraft(draft, user);

  const result = await aiService.validateOutreach(draft.draft_id, {
    draft_id: draft.draft_id,
    subject: draft.subject,
    body: draft.body,
  });

  const warnings = firstDefined(result?.warnings, result?.unsupported_claims, []);
  const unsupported = firstDefined(result?.unsupported_claims, draft.unsupported_claims);
  const hardFail = result?.valid === false || result?.ok === false;

  if (hardFail) {
    draft.warnings = warnings;
    draft.unsupported_claims = unsupported;
    await draft.save();
    throw new AppError('Outreach validation failed', 422, {
      code: 'OUTREACH_INVALID',
      errors: Array.isArray(warnings) ? warnings.map(String) : [String(warnings)],
      details: result,
    });
  }

  draft.warnings = warnings;
  draft.unsupported_claims = unsupported;
  draft.status = OUTREACH_DRAFT_STATUSES.VALIDATED;
  draft.validated_at = new Date();
  draft.raw = result;
  await draft.save();

  return {
    draft: draft.toObject(),
    validation: result,
    warnings,
  };
}

async function approveOutreach(draftId, user, body = {}) {
  const draft = await getDraftOrThrow(draftId);
  await assertCanAccessDraft(draft, user);

  if (draft.status !== OUTREACH_DRAFT_STATUSES.VALIDATED) {
    await validateOutreach(draftId, user);
  }

  const current = await getDraftOrThrow(draftId);

  const result = await aiService.approveOutreach({
    draft_id: current.draft_id,
    approved_by: body.approvedByName || user.id,
    notes: body.notes,
  });

  current.status = OUTREACH_DRAFT_STATUSES.APPROVED;
  current.approved_by = user._id;
  current.approved_at = new Date();
  current.raw = result;
  if (result?.warnings) {
    current.warnings = result.warnings;
  }
  await current.save();

  return {
    draft: current.toObject(),
    approval: result,
    warnings: current.warnings || [],
  };
}

async function sendOutreach(draftId, user, body) {
  const draft = await getDraftOrThrow(draftId);
  await assertCanAccessDraft(draft, user);

  if (draft.status !== OUTREACH_DRAFT_STATUSES.APPROVED) {
    throw new AppError('Outreach must be approved by a human before sending', 403, {
      code: 'OUTREACH_NOT_APPROVED',
    });
  }

  const result = await aiService.sendOutreach({
    draft_id: draft.draft_id,
    recipient_email: body.recipientEmail,
    approved_by: draft.approved_by?.toString() || user.id,
  });

  const sendId = firstDefined(result?.send_id, result?.sendId, result?.id, `send-${crypto.randomUUID()}`);
  const sentAt = firstDefined(result?.sent_at, result?.sentAt, new Date());
  const status = firstDefined(result?.status, 'SENT');

  draft.status = OUTREACH_DRAFT_STATUSES.SENT;
  draft.raw = result;
  await draft.save();

  const audit = await OutreachSendAudit.create({
    send_id: String(sendId),
    draft_id: draft.draft_id,
    companyId: draft.companyId,
    company: draft.company,
    recipient_email: body.recipientEmail,
    subject: draft.subject,
    body_preview: bodyPreview(draft.body),
    approved_by: draft.approved_by,
    sent_at: sentAt,
    status,
    error_message: firstDefined(result?.error_message, result?.errorMessage, ''),
    evidence: extractEvidence(result).concat(draft.evidence_used || []),
    raw: result,
  });

  return {
    draft: draft.toObject(),
    audit: audit.toObject(),
    warnings: result?.warnings || [],
  };
}

async function getCompanyOutreachAudit(companyId, user, query = {}) {
  const context = await loadCompanyAiContext(companyId);

  if (user.role !== USER_ROLES.ADMIN) {
    const visibleLead = await Lead.findOne({
      company: companyId,
      $or: [{ assignedTo: user._id }, { createdBy: user._id }],
    });

    if (!visibleLead) {
      throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
    }
  }

  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  const skip = (page - 1) * limit;

  const filter = { companyId: context.company._id };
  const [items, total] = await Promise.all([
    OutreachSendAudit.find(filter).sort({ sent_at: -1 }).skip(skip).limit(limit).lean(),
    OutreachSendAudit.countDocuments(filter),
  ]);

  return {
    companyId: context.company._id.toString(),
    audits: items,
    pagination: {
      page,
      limit,
      total,
      totalPages: total > 0 ? Math.ceil(total / limit) : 0,
    },
  };
}

module.exports = {
  generateOutreach,
  editOutreach,
  getOutreach,
  validateOutreach,
  approveOutreach,
  sendOutreach,
  getCompanyOutreachAudit,
};
