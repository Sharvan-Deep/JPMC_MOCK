const bearerSecurity = [{ bearerAuth: [] }];

const authErrors = {
  401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
  403: { description: 'Forbidden', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
};

const aiErrors = {
  ...authErrors,
  422: { description: 'AI request validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
  503: { description: 'AI service unavailable or timed out', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
};

const jsonData = (description) => ({
  description,
  content: {
    'application/json': {
      schema: {
        type: 'object',
        properties: {
          success: { type: 'boolean', example: true },
          data: { type: 'object' },
        },
      },
    },
  },
});

const companyIdParam = {
  name: 'companyId',
  in: 'path',
  required: true,
  schema: { type: 'string', format: 'objectId' },
};

const leadIdParam = {
  name: 'leadId',
  in: 'path',
  required: true,
  schema: { type: 'string', format: 'objectId' },
};

const draftIdParam = {
  name: 'id',
  in: 'path',
  required: true,
  schema: { type: 'string' },
  description: 'AI outreach draft_id',
};

const pageLimit = [
  { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
  { name: 'limit', in: 'query', schema: { type: 'integer', default: 20, maximum: 100 } },
];

const aiPaths = {
  '/api/ai/health': {
    get: {
      tags: ['AI'],
      summary: 'Proxy health check for the internal Python AI service',
      security: bearerSecurity,
      responses: {
        200: jsonData('AI service health'),
        ...aiErrors,
      },
    },
  },
  '/api/companies/discover': {
    post: {
      tags: ['AI'],
      summary: 'Search the AI document index and match existing MongoDB companies',
      description:
        'Does not crawl the web or create companies. Matches AI search hits to existing Company records by normalized name.',
      security: bearerSecurity,
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/DiscoverCompaniesRequest' } } },
      },
      responses: {
        200: jsonData('Discovery results'),
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...aiErrors,
      },
    },
  },
  '/api/companies/{companyId}/analyze': {
    post: {
      tags: ['AI'],
      summary: 'Analyze a company using stored CSR facts via the AI service',
      security: bearerSecurity,
      parameters: [companyIdParam],
      responses: {
        200: jsonData('Analysis persisted on Company.aiReadySummary'),
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...aiErrors,
      },
    },
  },
  '/api/companies/{companyId}/verify': {
    post: {
      tags: ['AI'],
      summary: 'Verify document changes and calculate freshness',
      security: bearerSecurity,
      parameters: [companyIdParam],
      responses: {
        200: jsonData('Freshness persisted with append-only history'),
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...aiErrors,
      },
    },
  },
  '/api/companies/{companyId}/freshness': {
    get: {
      tags: ['AI'],
      summary: 'Get latest stored freshness assessment',
      security: bearerSecurity,
      parameters: [companyIdParam],
      responses: {
        200: jsonData('Current freshness'),
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...authErrors,
      },
    },
  },
  '/api/companies/{companyId}/freshness/history': {
    get: {
      tags: ['AI'],
      summary: 'List stored freshness history',
      security: bearerSecurity,
      parameters: [companyIdParam, ...pageLimit],
      responses: {
        200: jsonData('Freshness history'),
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...authErrors,
      },
    },
  },
  '/api/companies/{companyId}/recommendations': {
    get: {
      tags: ['AI'],
      summary: 'List stored copilot recommendations for a company',
      security: bearerSecurity,
      parameters: [companyIdParam, ...pageLimit],
      responses: {
        200: jsonData('Recommendation history'),
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...authErrors,
      },
    },
  },
  '/api/companies/{companyId}/copilot/chat': {
    post: {
      tags: ['AI'],
      summary: 'Advisory copilot chat grounded in stored company facts',
      security: bearerSecurity,
      parameters: [companyIdParam],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/CopilotChatRequest' } } },
      },
      responses: {
        200: jsonData('Copilot response'),
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...aiErrors,
      },
    },
  },
  '/api/companies/{companyId}/outreach/audit': {
    get: {
      tags: ['Outreach'],
      summary: 'List outreach send audits for a company',
      security: bearerSecurity,
      parameters: [companyIdParam, ...pageLimit],
      responses: {
        200: jsonData('Send audit records'),
        ...authErrors,
      },
    },
  },
  '/api/leads/top': {
    get: {
      tags: ['AI'],
      summary: 'Highest-scoring prospects from stored AI lead scores',
      description: 'Uses MongoDB `Company.leadScore.total_score`. Does not call the AI service per row.',
      security: bearerSecurity,
      parameters: pageLimit,
      responses: {
        200: jsonData('Top scored leads'),
        ...authErrors,
      },
    },
  },
  '/api/leads/score-batch': {
    post: {
      tags: ['AI'],
      summary: 'Batch-score up to 20 manageable leads',
      security: bearerSecurity,
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/ScoreBatchRequest' } } },
      },
      responses: {
        200: jsonData('Persisted scores'),
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...aiErrors,
      },
    },
  },
  '/api/leads/{leadId}/score': {
    post: {
      tags: ['AI'],
      summary: 'Score a lead from stored company/CSR/freshness facts',
      description: 'Persists score history and Company.leadScore. Does not overwrite Lead.priority.',
      security: bearerSecurity,
      parameters: [leadIdParam],
      responses: {
        200: jsonData('Explainable score'),
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...aiErrors,
      },
    },
  },
  '/api/leads/{leadId}/recommend': {
    post: {
      tags: ['AI'],
      summary: 'Generate a copilot recommendation for a lead',
      description: 'Human approval remains required before outreach.',
      security: bearerSecurity,
      parameters: [leadIdParam],
      requestBody: {
        content: { 'application/json': { schema: { $ref: '#/components/schemas/RecommendRequest' } } },
      },
      responses: {
        200: jsonData('Persisted recommendation'),
        ...aiErrors,
      },
    },
  },
  '/api/leads/{leadId}/outreach/generate': {
    post: {
      tags: ['Outreach'],
      summary: 'Generate an outreach draft via the AI service',
      security: bearerSecurity,
      parameters: [leadIdParam],
      requestBody: {
        content: { 'application/json': { schema: { $ref: '#/components/schemas/OutreachGenerateRequest' } } },
      },
      responses: {
        201: jsonData('Draft created'),
        ...aiErrors,
      },
    },
  },
  '/api/outreach/{id}': {
    get: {
      tags: ['Outreach'],
      summary: 'Get a stored outreach draft',
      security: bearerSecurity,
      parameters: [draftIdParam],
      responses: {
        200: jsonData('Draft'),
        404: { description: 'Draft not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        ...authErrors,
      },
    },
  },
  '/api/outreach/{id}/edit': {
    post: {
      tags: ['Outreach'],
      summary: 'Edit an outreach draft',
      security: bearerSecurity,
      parameters: [draftIdParam],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/OutreachEditRequest' } } },
      },
      responses: {
        200: jsonData('Updated draft'),
        ...aiErrors,
      },
    },
  },
  '/api/outreach/{id}/validate': {
    post: {
      tags: ['Outreach'],
      summary: 'Validate an outreach draft before approval',
      security: bearerSecurity,
      parameters: [draftIdParam],
      responses: {
        200: jsonData('Validation result and warnings'),
        ...aiErrors,
      },
    },
  },
  '/api/outreach/{id}/approve': {
    post: {
      tags: ['Outreach'],
      summary: 'Record human approval of an outreach draft',
      security: bearerSecurity,
      parameters: [draftIdParam],
      requestBody: {
        content: { 'application/json': { schema: { $ref: '#/components/schemas/OutreachApproveRequest' } } },
      },
      responses: {
        200: jsonData('Approved draft'),
        ...aiErrors,
      },
    },
  },
  '/api/outreach/{id}/send': {
    post: {
      tags: ['Outreach'],
      summary: 'Send an approved outreach draft',
      description: 'Node rejects unapproved drafts with 403. AI 403 for unapproved send is preserved.',
      security: bearerSecurity,
      parameters: [draftIdParam],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/OutreachSendRequest' } } },
      },
      responses: {
        200: jsonData('Send audit record'),
        ...aiErrors,
      },
    },
  },
};

module.exports = aiPaths;
