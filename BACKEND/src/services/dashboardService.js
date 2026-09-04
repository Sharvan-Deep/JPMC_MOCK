const { Company, Lead, LeadActivity } = require('../models');
const { toSafeUser } = require('../utils/userSerializer');
const {
  LEAD_STATUSES,
  ACTIVE_LEAD_STATUSES,
  LEAD_PRIORITIES,
} = require('../config/constants');

const USER_POPULATE_FIELDS = 'name email role isActive';
const COMPANY_NAME_FIELDS = 'company_name';
const RECENT_ACTIVITY_WINDOW_DAYS = 30;

/**
 * @param {import('mongoose').Document | object} lead
 */
function toDashboardLead(lead) {
  const obj = lead.toObject ? lead.toObject() : lead;
  const company = obj.companyDoc || obj.company;
  const companyObj = company?.toObject ? company.toObject() : company;
  const assignedUser = obj.assignedUser || obj.assignedTo;
  const assignedObj = assignedUser?.toObject ? assignedUser.toObject() : assignedUser;

  return {
    id: obj._id,
    company: companyObj
      ? {
          id: companyObj._id,
          company_name: companyObj.company_name,
        }
      : null,
    status: obj.status,
    priority: obj.priority,
    assignedTo: toSafeUser(assignedObj),
    createdAt: obj.createdAt,
    updatedAt: obj.updatedAt,
  };
}

/**
 * @param {Array<{ _id: string, count: number }>} rows
 */
function mapCountRows(rows) {
  return rows.reduce((acc, row) => {
    if (row._id) {
      acc[row._id] = row.count;
    }
    return acc;
  }, {});
}

/**
 * @param {Record<string, number>} counts
 */
function buildStatusDistribution(counts) {
  return Object.values(LEAD_STATUSES).reduce((acc, status) => {
    acc[status] = counts[status] || 0;
    return acc;
  }, {});
}

async function getDashboardSummary() {
  const recentActivitySince = new Date(
    Date.now() - RECENT_ACTIVITY_WINDOW_DAYS * 24 * 60 * 60 * 1000
  );

  const [
    totalCompanies,
    washAggregation,
    companiesWithWASH,
    totalLeads,
    activeLeads,
    wonLeads,
    lostLeads,
    leadStatusRows,
    recentActivityCount,
    activityTypeRows,
  ] = await Promise.all([
    Company.countDocuments(),
    Company.aggregate([
      {
        $group: {
          _id: null,
          totalWASHSpend: { $sum: '$total_wash_spend_crore' },
          totalWaterSpend: { $sum: '$total_water_spend_crore' },
          totalSanitationSpend: { $sum: '$total_sanitation_spend_crore' },
        },
      },
    ]),
    Company.countDocuments({
      $or: [{ wash_record_count: { $gt: 0 } }, { total_wash_spend_crore: { $gt: 0 } }],
    }),
    Lead.countDocuments(),
    Lead.countDocuments({ status: { $in: ACTIVE_LEAD_STATUSES } }),
    Lead.countDocuments({ status: LEAD_STATUSES.WON }),
    Lead.countDocuments({ status: LEAD_STATUSES.LOST }),
    Lead.aggregate([{ $group: { _id: '$status', count: { $sum: 1 } } }]),
    LeadActivity.countDocuments({ createdAt: { $gte: recentActivitySince } }),
    LeadActivity.aggregate([{ $group: { _id: '$activityType', count: { $sum: 1 } } }]),
  ]);

  const washTotals = washAggregation[0] || {
    totalWASHSpend: 0,
    totalWaterSpend: 0,
    totalSanitationSpend: 0,
  };

  const leadStatusCounts = mapCountRows(leadStatusRows);

  return {
    companies: {
      total: totalCompanies,
    },
    wash: {
      companiesWithWASH,
      totalWASHSpend: washTotals.totalWASHSpend,
      totalWaterSpend: washTotals.totalWaterSpend,
      totalSanitationSpend: washTotals.totalSanitationSpend,
    },
    leads: {
      total: totalLeads,
      active: activeLeads,
      won: wonLeads,
      lost: lostLeads,
      byStatus: buildStatusDistribution(leadStatusCounts),
    },
    activities: {
      recentCount: recentActivityCount,
      recentWindowDays: RECENT_ACTIVITY_WINDOW_DAYS,
      byType: mapCountRows(activityTypeRows),
    },
  };
}

/**
 * @param {{ page: number, limit: number }} query
 */
async function getTopProspects(query) {
  const skip = (query.page - 1) * query.limit;
  const matchStage = { status: { $in: ACTIVE_LEAD_STATUSES } };

  const [result] = await Lead.aggregate([
    { $match: matchStage },
    {
      $addFields: {
        priorityOrder: {
          $switch: {
            branches: [
              { case: { $eq: ['$priority', LEAD_PRIORITIES.HIGH] }, then: 1 },
              { case: { $eq: ['$priority', LEAD_PRIORITIES.MEDIUM] }, then: 2 },
              { case: { $eq: ['$priority', LEAD_PRIORITIES.LOW] }, then: 3 },
            ],
            default: 4,
          },
        },
      },
    },
    { $sort: { priorityOrder: 1, updatedAt: -1, createdAt: -1 } },
    {
      $facet: {
        prospects: [
          { $skip: skip },
          { $limit: query.limit },
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
            $lookup: {
              from: 'users',
              localField: 'assignedTo',
              foreignField: '_id',
              as: 'assignedUser',
            },
          },
          { $unwind: '$assignedUser' },
          {
            $project: {
              companyDoc: { _id: 1, company_name: 1 },
              assignedUser: {
                _id: 1,
                name: 1,
                email: 1,
                role: 1,
                isActive: 1,
                isEmailVerified: 1,
                lastLoginAt: 1,
                createdAt: 1,
                updatedAt: 1,
              },
              status: 1,
              priority: 1,
              createdAt: 1,
              updatedAt: 1,
            },
          },
        ],
        total: [{ $count: 'count' }],
      },
    },
  ]);

  const total = result.total[0]?.count || 0;

  return {
    prospects: result.prospects.map(toDashboardLead),
    pagination: {
      page: query.page,
      limit: query.limit,
      total,
      totalPages: Math.ceil(total / query.limit) || 0,
    },
  };
}

/**
 * @param {{ page: number, limit: number }} query
 */
async function getRecentLeads(query) {
  const skip = (query.page - 1) * query.limit;

  const [leads, total] = await Promise.all([
    Lead.find()
      .sort({ updatedAt: -1, createdAt: -1 })
      .skip(skip)
      .limit(query.limit)
      .populate('company', COMPANY_NAME_FIELDS)
      .populate('assignedTo', USER_POPULATE_FIELDS)
      .lean(),
    Lead.countDocuments(),
  ]);

  return {
    leads: leads.map(toDashboardLead),
    pagination: {
      page: query.page,
      limit: query.limit,
      total,
      totalPages: Math.ceil(total / query.limit) || 0,
    },
  };
}

/**
 * Follow-up queue uses leads in FOLLOW_UP status, ordered by oldest updatedAt first.
 * No dedicated follow-up date exists in the schema.
 *
 * @param {{ page: number, limit: number }} query
 */
async function getFollowUps(query) {
  const skip = (query.page - 1) * query.limit;
  const filter = { status: LEAD_STATUSES.FOLLOW_UP };

  const [leads, total] = await Promise.all([
    Lead.find(filter)
      .sort({ updatedAt: 1, createdAt: 1 })
      .skip(skip)
      .limit(query.limit)
      .populate('company', COMPANY_NAME_FIELDS)
      .populate('assignedTo', USER_POPULATE_FIELDS)
      .lean(),
    Lead.countDocuments(filter),
  ]);

  return {
    followUps: leads.map(toDashboardLead),
    pagination: {
      page: query.page,
      limit: query.limit,
      total,
      totalPages: Math.ceil(total / query.limit) || 0,
    },
  };
}

module.exports = {
  getDashboardSummary,
  getTopProspects,
  getRecentLeads,
  getFollowUps,
  toDashboardLead,
};
