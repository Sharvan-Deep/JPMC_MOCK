const {
  USER_ROLES,
  INVITATION_STATUSES,
  LEAD_STATUSES,
  LEAD_PRIORITIES,
  LEAD_ACTIVITY_TYPES,
} = require('../constants');

const manualActivityTypes = Object.values(LEAD_ACTIVITY_TYPES).filter(
  (type) => type !== LEAD_ACTIVITY_TYPES.STATUS_CHANGED
);

const schemas = {
  ErrorResponse: {
    type: 'object',
    properties: {
      success: { type: 'boolean', example: false },
      message: { type: 'string' },
      code: { type: 'string' },
      errors: {
        type: 'array',
        items: { type: 'string' },
      },
    },
    required: ['success', 'message'],
  },
  SuccessResponse: {
    type: 'object',
    properties: {
      success: { type: 'boolean', example: true },
      message: { type: 'string' },
    },
    required: ['success'],
  },
  Pagination: {
    type: 'object',
    properties: {
      page: { type: 'integer', example: 1 },
      limit: { type: 'integer', example: 20 },
      total: { type: 'integer', example: 0 },
      totalPages: { type: 'integer', example: 0 },
    },
  },
  User: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      name: { type: 'string' },
      email: { type: 'string', format: 'email' },
      role: { type: 'string', enum: Object.values(USER_ROLES) },
      isActive: { type: 'boolean' },
      isEmailVerified: { type: 'boolean' },
      lastLoginAt: { type: 'string', format: 'date-time', nullable: true },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  LoginRequest: {
    type: 'object',
    required: ['email', 'password'],
    properties: {
      email: { type: 'string', format: 'email' },
      password: { type: 'string' },
    },
  },
  LoginResponse: {
    type: 'object',
    properties: {
      success: { type: 'boolean', example: true },
      data: {
        type: 'object',
        properties: {
          accessToken: { type: 'string' },
          user: { $ref: '#/components/schemas/User' },
        },
      },
    },
  },
  RefreshResponse: {
    type: 'object',
    properties: {
      success: { type: 'boolean', example: true },
      data: {
        type: 'object',
        properties: {
          accessToken: { type: 'string' },
        },
      },
    },
  },
  ForgotPasswordRequest: {
    type: 'object',
    required: ['email'],
    properties: {
      email: { type: 'string', format: 'email' },
    },
  },
  ResetPasswordRequest: {
    type: 'object',
    required: ['token', 'password'],
    properties: {
      token: { type: 'string' },
      password: {
        type: 'string',
        description: 'Min 8 chars, at least one letter and one number',
      },
    },
  },
  CreateInvitationRequest: {
    type: 'object',
    required: ['name', 'email'],
    properties: {
      name: { type: 'string', maxLength: 150 },
      email: { type: 'string', format: 'email' },
    },
  },
  Invitation: {
    type: 'object',
    properties: {
      _id: { type: 'string', format: 'objectId' },
      name: { type: 'string' },
      email: { type: 'string', format: 'email' },
      role: { type: 'string', enum: Object.values(USER_ROLES) },
      status: { type: 'string', enum: Object.values(INVITATION_STATUSES) },
      expiresAt: { type: 'string', format: 'date-time' },
      invitedBy: {
        type: 'object',
        properties: {
          _id: { type: 'string', format: 'objectId' },
          name: { type: 'string' },
          email: { type: 'string', format: 'email' },
        },
      },
      acceptedAt: { type: 'string', format: 'date-time', nullable: true },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  VerifyInvitationRequest: {
    type: 'object',
    required: ['token'],
    properties: {
      token: { type: 'string' },
    },
  },
  ActivateAccountRequest: {
    type: 'object',
    required: ['token', 'password'],
    properties: {
      token: { type: 'string' },
      password: { type: 'string' },
      name: { type: 'string', maxLength: 150 },
    },
  },
  InvitationImportSummary: {
    type: 'object',
    properties: {
      totalRows: { type: 'integer' },
      created: { type: 'integer' },
      skipped: { type: 'integer' },
      failed: { type: 'integer' },
      errors: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            row: { type: 'integer' },
            email: { type: 'string' },
            errors: { type: 'array', items: { type: 'string' } },
          },
        },
      },
    },
  },
  UpdateUserRequest: {
    type: 'object',
    required: ['name'],
    properties: {
      name: { type: 'string', maxLength: 150 },
    },
  },
  UpdateUserRoleRequest: {
    type: 'object',
    required: ['role'],
    properties: {
      role: { type: 'string', enum: Object.values(USER_ROLES) },
    },
  },
  UpdateUserStatusRequest: {
    type: 'object',
    required: ['isActive'],
    properties: {
      isActive: { type: 'boolean' },
    },
  },
  Company: {
    type: 'object',
    properties: {
      _id: { type: 'string', format: 'objectId' },
      company_name: { type: 'string' },
      wash_record_count: { type: 'number' },
      financial_years: { type: 'array', items: { type: 'string' } },
      states: { type: 'array', items: { type: 'string' } },
      csr_sectors: { type: 'array', items: { type: 'string' } },
      total_wash_spend_crore: { type: 'number' },
      latest_financial_year: { type: 'string' },
      total_water_spend_crore: { type: 'number' },
      total_sanitation_spend_crore: { type: 'number' },
      water_active_years: { type: 'array', items: { type: 'string' } },
      sanitation_active_years: { type: 'array', items: { type: 'string' } },
      wash_focus_evidence: { type: 'string' },
      source: { type: 'string' },
      source_retrieved_date: { type: 'string', format: 'date-time', nullable: true },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  CompanySummary: {
    type: 'object',
    properties: {
      _id: { type: 'string', format: 'objectId' },
      company_name: { type: 'string' },
      wash_record_count: { type: 'number' },
      financial_years: { type: 'array', items: { type: 'string' } },
      states: { type: 'array', items: { type: 'string' } },
      csr_sectors: { type: 'array', items: { type: 'string' } },
      total_wash_spend_crore: { type: 'number' },
      latest_financial_year: { type: 'string' },
      total_water_spend_crore: { type: 'number' },
      total_sanitation_spend_crore: { type: 'number' },
      water_active_years: { type: 'array', items: { type: 'string' } },
      sanitation_active_years: { type: 'array', items: { type: 'string' } },
      wash_focus_evidence: { type: 'string' },
      source: { type: 'string' },
      source_retrieved_date: { type: 'string', format: 'date-time', nullable: true },
    },
  },
  CSRPolicy: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      financialYear: { type: 'string' },
      title: { type: 'string' },
      policyText: { type: 'string' },
      policyUrl: { type: 'string' },
      source: { type: 'string' },
      retrievedAt: { type: 'string', format: 'date-time', nullable: true },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  CSRActivity: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      financialYear: { type: 'string' },
      psuStatus: { type: 'string' },
      state: { type: 'string' },
      developmentSector: { type: 'string' },
      subDevelopmentSector: { type: 'string' },
      amountSpentCrore: { type: 'number' },
      sourceName: { type: 'string' },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  Source: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      sourceType: { type: 'string' },
      sourceName: { type: 'string' },
      sourceUrl: { type: 'string' },
      retrievedAt: { type: 'string', format: 'date-time', nullable: true },
      createdAt: { type: 'string', format: 'date-time' },
    },
  },
  CSROverview: {
    type: 'object',
    properties: {
      company: {
        type: 'object',
        properties: {
          id: { type: 'string', format: 'objectId' },
          company_name: { type: 'string' },
        },
      },
      policyCount: { type: 'integer' },
      sourceCount: { type: 'integer' },
      availableFinancialYears: { type: 'array', items: { type: 'string' } },
      washSummary: { $ref: '#/components/schemas/CompanySummary' },
      recentPolicies: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            id: { type: 'string', format: 'objectId' },
            financialYear: { type: 'string' },
            title: { type: 'string' },
            policyUrl: { type: 'string' },
            source: { type: 'string' },
            retrievedAt: { type: 'string', format: 'date-time', nullable: true },
          },
        },
      },
      activities: {
        type: 'object',
        properties: {
          count: { type: 'integer' },
          totalSpendCrore: { type: 'number' },
          financialYears: { type: 'array', items: { type: 'string' } },
          recent: {
            type: 'array',
            items: { $ref: '#/components/schemas/CSRActivity' },
          },
        },
      },
    },
  },
  Lead: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      company: {
        type: 'object',
        nullable: true,
        properties: {
          id: { type: 'string', format: 'objectId' },
          company_name: { type: 'string' },
          states: { type: 'array', items: { type: 'string' } },
          csr_sectors: { type: 'array', items: { type: 'string' } },
          latest_financial_year: { type: 'string' },
          total_wash_spend_crore: { type: 'number' },
          wash_record_count: { type: 'number' },
        },
      },
      assignedTo: { $ref: '#/components/schemas/User' },
      createdBy: { $ref: '#/components/schemas/User' },
      status: { type: 'string', enum: Object.values(LEAD_STATUSES) },
      priority: { type: 'string', enum: Object.values(LEAD_PRIORITIES) },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  LeadNote: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      lead: { type: 'string', format: 'objectId' },
      user: { $ref: '#/components/schemas/User' },
      note: { type: 'string', maxLength: 5000 },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
    },
  },
  LeadActivity: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'objectId' },
      lead: { type: 'string', format: 'objectId' },
      user: { $ref: '#/components/schemas/User' },
      activityType: { type: 'string', enum: Object.values(LEAD_ACTIVITY_TYPES) },
      description: { type: 'string', maxLength: 2000 },
      createdAt: { type: 'string', format: 'date-time' },
    },
  },
  CreateLeadRequest: {
    type: 'object',
    required: ['companyId'],
    properties: {
      companyId: { type: 'string', format: 'objectId' },
      priority: { type: 'string', enum: Object.values(LEAD_PRIORITIES) },
    },
  },
  UpdateLeadRequest: {
    type: 'object',
    properties: {
      status: { type: 'string', enum: Object.values(LEAD_STATUSES) },
      priority: { type: 'string', enum: Object.values(LEAD_PRIORITIES) },
      assignedTo: { type: 'string', format: 'objectId' },
    },
  },
  AssignLeadRequest: {
    type: 'object',
    required: ['userId'],
    properties: {
      userId: { type: 'string', format: 'objectId' },
    },
  },
  CreateLeadNoteRequest: {
    type: 'object',
    required: ['note'],
    properties: {
      note: { type: 'string', maxLength: 5000 },
    },
  },
  CreateLeadActivityRequest: {
    type: 'object',
    required: ['activityType'],
    properties: {
      activityType: { type: 'string', enum: manualActivityTypes },
      description: { type: 'string', maxLength: 2000 },
    },
  },
  DashboardSummary: {
    type: 'object',
    properties: {
      companies: {
        type: 'object',
        properties: { total: { type: 'integer' } },
      },
      wash: {
        type: 'object',
        properties: {
          companiesWithWASH: { type: 'integer' },
          totalWASHSpend: { type: 'number' },
          totalWaterSpend: { type: 'number' },
          totalSanitationSpend: { type: 'number' },
        },
      },
      leads: {
        type: 'object',
        properties: {
          total: { type: 'integer' },
          active: { type: 'integer' },
          won: { type: 'integer' },
          lost: { type: 'integer' },
          byStatus: { type: 'object', additionalProperties: { type: 'integer' } },
        },
      },
      activities: {
        type: 'object',
        properties: {
          recentCount: { type: 'integer' },
          recentWindowDays: { type: 'integer' },
          byType: { type: 'object', additionalProperties: { type: 'integer' } },
        },
      },
    },
  },
  AiEvidence: {
    type: 'object',
    properties: {
      company: { type: 'string' },
      financial_year: { type: 'string' },
      document_type: { type: 'string' },
      document_version: { type: 'string' },
      page: {},
      source_url: { type: 'string' },
      relevant_source_text: { type: 'string' },
      document_hash: { type: 'string' },
    },
  },
  DiscoverCompaniesRequest: {
    type: 'object',
    required: ['query'],
    properties: {
      query: { type: 'string', example: 'water CSR Maharashtra' },
      limit: { type: 'integer', minimum: 1, maximum: 50, example: 10 },
    },
  },
  CopilotChatRequest: {
    type: 'object',
    required: ['message'],
    properties: {
      message: { type: 'string', example: 'Summarize WASH evidence for outreach' },
    },
  },
  RecommendRequest: {
    type: 'object',
    properties: {
      notes: { type: 'string' },
    },
  },
  OutreachGenerateRequest: {
    type: 'object',
    properties: {
      tone: { type: 'string', enum: ['formal', 'professional', 'warm', 'concise'] },
      recipientRole: {
        type: 'string',
        enum: ['csr_head', 'sustainability_lead', 'ceo', 'foundation_contact', 'other'],
      },
    },
  },
  OutreachEditRequest: {
    type: 'object',
    properties: {
      subject: { type: 'string' },
      body: { type: 'string' },
      instruction: { type: 'string' },
      tone: { type: 'string', enum: ['formal', 'professional', 'warm', 'concise'] },
    },
  },
  OutreachApproveRequest: {
    type: 'object',
    properties: {
      notes: { type: 'string' },
      approvedByName: { type: 'string' },
    },
  },
  OutreachSendRequest: {
    type: 'object',
    required: ['recipientEmail'],
    properties: {
      recipientEmail: { type: 'string', format: 'email', example: 'csr@example.com' },
    },
  },
  ScoreBatchRequest: {
    type: 'object',
    required: ['leadIds'],
    properties: {
      leadIds: {
        type: 'array',
        maxItems: 20,
        items: { type: 'string', format: 'objectId' },
      },
    },
  },
};

module.exports = {
  schemas,
  manualActivityTypes,
};
