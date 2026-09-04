const { Lead, Company, CompanyLeadScore } = require('../models');
const aiService = require('./aiService');
const { loadCompanyAiContext, buildCandidateScoringInput } = require('./aiContextService');
const { persistLeadScore } = require('./companyAiService');
const leadService = require('./leadService');
const { toSafeUser } = require('../utils/userSerializer');
const { AppError } = require('../utils/errors');
const { USER_ROLES } = require('../config/constants');

async function getManagedLead(leadId, user) {
  const lead = await Lead.findById(leadId);

  if (!lead) {
    throw new AppError('Lead not found', 404, { code: 'LEAD_NOT_FOUND' });
  }

  if (!leadService.canManageLead(lead, user)) {
    throw new AppError('Forbidden', 403, { code: 'FORBIDDEN' });
  }

  return lead;
}

function toTopLead(lead) {
  const obj = lead.toObject ? lead.toObject() : lead;

  return {
    id: obj._id,
    company: obj.company
      ? {
          id: obj.company._id,
          company_name: obj.company.company_name,
          states: obj.company.states,
          csr_sectors: obj.company.csr_sectors,
          latest_financial_year: obj.company.latest_financial_year,
          total_wash_spend_crore: obj.company.total_wash_spend_crore,
          wash_record_count: obj.company.wash_record_count,
          leadScore: obj.company.leadScore || null,
        }
      : null,
    assignedTo: toSafeUser(obj.assignedTo),
    createdBy: toSafeUser(obj.createdBy),
    status: obj.status,
    priority: obj.priority,
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

async function scoreLead(leadId, user) {
  const lead = await getManagedLead(leadId, user);
  const context = await loadCompanyAiContext(lead.company.toString());
  const scoringInput = buildCandidateScoringInput(context);
  const score = await aiService.scoreCandidate(scoringInput);
  const snapshot = await persistLeadScore(context.company, score);

  return {
    leadId: lead._id.toString(),
    companyId: context.company._id.toString(),
    score: snapshot,
    warnings: score?.warnings || [],
    leadPriorityUnchanged: lead.priority,
    note: 'Lead.priority is staff-managed and is not overwritten by AI scoring.',
  };
}

async function scoreLeadsBatch(leadIds, user) {
  if (!Array.isArray(leadIds) || leadIds.length === 0) {
    throw new AppError('leadIds is required', 400, { errors: ['leadIds is required'] });
  }

  if (leadIds.length > 20) {
    throw new AppError('A maximum of 20 leads can be scored per batch', 400);
  }

  const inputs = [];

  for (const leadId of leadIds) {
    const lead = await getManagedLead(leadId, user);
    const context = await loadCompanyAiContext(lead.company.toString());
    inputs.push(buildCandidateScoringInput(context));
  }

  const batch = await aiService.scoreCandidatesBatch({ candidates: inputs });
  const scores = Array.isArray(batch) ? batch : batch?.scores || batch?.results || [];
  const persisted = [];

  for (let i = 0; i < inputs.length; i += 1) {
    const score = scores[i];
    if (!score) {
      continue;
    }

    const company = await Company.findById(inputs[i].company_id);
    if (company) {
      persisted.push(await persistLeadScore(company, score));
    }
  }

  return {
    scores: persisted,
    warnings: batch?.warnings || [],
  };
}

async function listTopLeads(query = {}, user) {
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 10));
  const skip = (page - 1) * limit;

  const pipeline = [
    {
      $lookup: {
        from: 'companies',
        localField: 'company',
        foreignField: '_id',
        as: 'companyDoc',
      },
    },
    { $unwind: '$companyDoc' },
    {
      $match: {
        'companyDoc.leadScore.total_score': { $type: 'number' },
      },
    },
  ];

  if (user.role !== USER_ROLES.ADMIN) {
    pipeline.push({
      $match: {
        $or: [{ assignedTo: user._id }, { createdBy: user._id }],
      },
    });
  }

  pipeline.push({
    $facet: {
      items: [
        { $sort: { 'companyDoc.leadScore.total_score': -1, createdAt: -1 } },
        { $skip: skip },
        { $limit: limit },
      ],
      total: [{ $count: 'count' }],
    },
  });

  const [facet] = await Lead.aggregate(pipeline);
  const items = facet?.items || [];
  const total = facet?.total?.[0]?.count || 0;
  const order = new Map(items.map((row, index) => [row._id.toString(), index]));

  const leads = await Lead.find({ _id: { $in: items.map((row) => row._id) } })
    .populate(
      'company',
      'company_name states csr_sectors latest_financial_year total_wash_spend_crore wash_record_count leadScore'
    )
    .populate('assignedTo', 'name email role isActive')
    .populate('createdBy', 'name email role isActive');

  const sorted = leads
    .sort((a, b) => (order.get(a._id.toString()) ?? 0) - (order.get(b._id.toString()) ?? 0))
    .map(toTopLead);

  return {
    leads: sorted,
    pagination: {
      page,
      limit,
      total,
      totalPages: total > 0 ? Math.ceil(total / limit) : 0,
    },
  };
}

async function getScoreHistory(companyId) {
  return CompanyLeadScore.find({ companyId }).sort({ scored_at: -1 }).limit(20).lean();
}

module.exports = {
  scoreLead,
  scoreLeadsBatch,
  listTopLeads,
  getManagedLead,
  getScoreHistory,
};
