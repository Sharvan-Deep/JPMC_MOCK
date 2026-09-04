const aiService = require('./aiService');
const { loadCompanyAiContext, buildCanonicalCompanyPayload } = require('./aiContextService');
const { persistRecommendation } = require('./companyAiService');
const { getManagedLead } = require('./leadScoringService');

async function recommendForLead(leadId, user, body = {}) {
  const lead = await getManagedLead(leadId, user);
  const context = await loadCompanyAiContext(lead.company.toString());
  const canonical = buildCanonicalCompanyPayload(context);

  const recommendation = await aiService.recommend({
    company_id: canonical.company_id,
    company: canonical.company,
    score: canonical.lead_score,
    freshness: canonical.freshness,
    notes: body.notes,
    ...canonical,
    human_approval_required: true,
  });

  const snapshot = await persistRecommendation(context.company, recommendation);

  return {
    leadId: lead._id.toString(),
    companyId: canonical.company_id,
    recommendation: snapshot,
    warnings: recommendation?.warnings || [],
    human_approval_required: true,
  };
}

module.exports = {
  recommendForLead,
};
