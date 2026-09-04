const { Company, CSRActivity, CSRPolicy, Source } = require('../models');
const { AppError } = require('../utils/errors');
const { isValidObjectId } = require('../utils/objectId');

/**
 * Load company plus related CSR records used to construct AI requests.
 * @param {string} companyId
 */
async function loadCompanyAiContext(companyId) {
  if (!isValidObjectId(companyId)) {
    throw new AppError('Invalid company ID', 400, { code: 'INVALID_ID' });
  }

  const company = await Company.findById(companyId).lean();

  if (!company) {
    throw new AppError('Company not found', 404, { code: 'COMPANY_NOT_FOUND' });
  }

  const [activities, policies, sources] = await Promise.all([
    CSRActivity.find({ company: companyId }).sort({ financialYear: -1, createdAt: -1 }).limit(50).lean(),
    CSRPolicy.find({ company: companyId }).sort({ createdAt: -1 }).limit(20).lean(),
    Source.find({ company: companyId }).sort({ createdAt: -1 }).limit(20).lean(),
  ]);

  return { company, activities, policies, sources };
}

/**
 * Canonical company facts for AI payloads. No inferred WASH-loss claims.
 * @param {{ company: object, activities?: object[], policies?: object[], sources?: object[] }} context
 */
function buildCanonicalCompanyPayload(context) {
  const { company, activities = [], policies = [], sources = [] } = context;
  const companyId = company._id.toString();

  return {
    company_id: companyId,
    company: company.company_name,
    wash_record_count: company.wash_record_count,
    financial_years: company.financial_years || [],
    states: company.states || [],
    csr_sectors: company.csr_sectors || [],
    total_wash_spend_crore: company.total_wash_spend_crore,
    latest_financial_year: company.latest_financial_year,
    total_water_spend_crore: company.total_water_spend_crore,
    total_sanitation_spend_crore: company.total_sanitation_spend_crore,
    water_active_years: company.water_active_years || [],
    sanitation_active_years: company.sanitation_active_years || [],
    wash_focus_evidence: company.wash_focus_evidence || '',
    source: company.source || '',
    source_retrieved_date: company.source_retrieved_date,
    freshness: company.freshness || null,
    lead_score: company.leadScore || null,
    missing_evidence_does_not_imply_wash_loss: true,
    csr_activities: activities.map((row) => ({
      financial_year: row.financialYear,
      psu_status: row.psuStatus,
      state: row.state,
      development_sector: row.developmentSector,
      sub_development_sector: row.subDevelopmentSector,
      amount_spent_crore: row.amountSpentCrore,
      source_name: row.sourceName,
    })),
    csr_policies: policies.map((row) => ({
      financial_year: row.financialYear,
      title: row.title,
      policy_url: row.policyUrl,
      source: row.source,
    })),
    sources: sources.map((row) => ({
      source_type: row.sourceType,
      source_name: row.sourceName,
      source_url: row.sourceUrl,
      retrieved_at: row.retrievedAt,
    })),
  };
}

function buildDocumentText(payload) {
  const lines = [
    `Company: ${payload.company}`,
    `Latest financial year: ${payload.latest_financial_year || ''}`,
    `WASH record count: ${payload.wash_record_count ?? ''}`,
    `Total WASH spend (crore): ${payload.total_wash_spend_crore ?? ''}`,
    `States: ${(payload.states || []).join(', ')}`,
    `CSR sectors: ${(payload.csr_sectors || []).join(', ')}`,
    `WASH focus evidence: ${payload.wash_focus_evidence || ''}`,
  ];

  if (payload.csr_activities.length) {
    lines.push('CSR activities:');
    payload.csr_activities.slice(0, 20).forEach((row) => {
      lines.push(
        `- ${row.financial_year || ''} ${row.state || ''} ${row.development_sector || ''} ${row.amount_spent_crore ?? ''}`
      );
    });
  }

  return lines.filter(Boolean).join('\n');
}

function buildCandidateScoringInput(context) {
  const canonical = buildCanonicalCompanyPayload(context);

  return {
    company_id: canonical.company_id,
    company: canonical.company,
    ...canonical,
  };
}

module.exports = {
  loadCompanyAiContext,
  buildCanonicalCompanyPayload,
  buildDocumentText,
  buildCandidateScoringInput,
};
