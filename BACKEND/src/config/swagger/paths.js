const bearerSecurity = [{ bearerAuth: [] }];

const companySortFields = [
  'company_name',
  'wash_record_count',
  'latest_financial_year',
  'total_wash_spend_crore',
  'total_water_spend_crore',
  'total_sanitation_spend_crore',
  'createdAt',
  'updatedAt',
];

const paths = {
  '/health': {
    get: {
      tags: ['System'],
      summary: 'Health check',
      responses: {
        200: {
          description: 'Service is running',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  status: { type: 'string', example: 'ok' },
                  service: { type: 'string', example: 'jaldhaara-backend' },
                },
              },
            },
          },
        },
      },
    },
  },
  '/api/auth/login': {
    post: {
      tags: ['Auth'],
      summary: 'Login with email and password',
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/LoginRequest' } } },
      },
      responses: {
        200: {
          description: 'Login successful; refresh token set in httpOnly cookie',
          content: { 'application/json': { schema: { $ref: '#/components/schemas/LoginResponse' } } },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Invalid credentials', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/refresh': {
    post: {
      tags: ['Auth'],
      summary: 'Refresh access token',
      description: 'Uses the `refreshToken` httpOnly cookie set at login.',
      responses: {
        200: { description: 'New access token', content: { 'application/json': { schema: { $ref: '#/components/schemas/RefreshResponse' } } } },
        401: { description: 'Invalid or missing refresh token', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/logout': {
    post: {
      tags: ['Auth'],
      summary: 'Logout and revoke refresh session',
      description: 'Clears the `refreshToken` cookie.',
      responses: {
        200: { description: 'Logged out', content: { 'application/json': { schema: { $ref: '#/components/schemas/SuccessResponse' } } } },
      },
    },
  },
  '/api/auth/me': {
    get: {
      tags: ['Auth'],
      summary: 'Get current authenticated user',
      security: bearerSecurity,
      responses: {
        200: {
          description: 'Current user profile',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/User' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/forgot-password': {
    post: {
      tags: ['Auth'],
      summary: 'Request password reset email',
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/ForgotPasswordRequest' } } },
      },
      responses: {
        200: { description: 'Generic success message', content: { 'application/json': { schema: { $ref: '#/components/schemas/SuccessResponse' } } } },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/reset-password': {
    post: {
      tags: ['Auth'],
      summary: 'Reset password using one-time token',
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/ResetPasswordRequest' } } },
      },
      responses: {
        200: { description: 'Password reset successful', content: { 'application/json': { schema: { $ref: '#/components/schemas/SuccessResponse' } } } },
        400: { description: 'Invalid token or validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/invitations': {
    post: {
      tags: ['Auth', 'Invitations'],
      summary: 'Create user invitation (Admin)',
      security: bearerSecurity,
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/CreateInvitationRequest' } } },
      },
      responses: {
        201: {
          description: 'Invitation created',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  message: { type: 'string' },
                  data: { $ref: '#/components/schemas/Invitation' },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    get: {
      tags: ['Auth', 'Invitations'],
      summary: 'List invitations (Admin)',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1, minimum: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 20, minimum: 1, maximum: 100 } },
        { name: 'status', in: 'query', schema: { type: 'string', enum: ['PENDING', 'ACCEPTED', 'EXPIRED', 'REVOKED'] } },
        { name: 'search', in: 'query', schema: { type: 'string' }, description: 'Search name or email' },
        { name: 'sort', in: 'query', schema: { type: 'string', enum: ['createdAt', 'expiresAt', 'name', 'email', 'status'], default: 'createdAt' } },
        { name: 'order', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'], default: 'desc' } },
      ],
      responses: {
        200: {
          description: 'Invitation list',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'array', items: { $ref: '#/components/schemas/Invitation' } },
                  pagination: { $ref: '#/components/schemas/Pagination' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/invitations/verify': {
    post: {
      tags: ['Auth', 'Invitations'],
      summary: 'Verify invitation token',
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/VerifyInvitationRequest' } } },
      },
      responses: {
        200: { description: 'Token valid', content: { 'application/json': { schema: { type: 'object', properties: { success: { type: 'boolean' }, data: { type: 'object' } } } } } },
        400: { description: 'Invalid or expired token', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/invitations/import': {
    post: {
      tags: ['Auth', 'Invitations'],
      summary: 'Bulk import invitations from CSV (Admin)',
      security: bearerSecurity,
      requestBody: {
        required: true,
        content: {
          'multipart/form-data': {
            schema: {
              type: 'object',
              required: ['file'],
              properties: {
                file: { type: 'string', format: 'binary', description: 'CSV with columns: name, email' },
              },
            },
          },
        },
      },
      responses: {
        200: {
          description: 'Import summary',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/InvitationImportSummary' },
                },
              },
            },
          },
        },
        400: { description: 'Missing or invalid CSV', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/invitations/{invitationId}': {
    get: {
      tags: ['Auth', 'Invitations'],
      summary: 'Get invitation by ID (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'invitationId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Invitation details',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/Invitation' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    delete: {
      tags: ['Auth', 'Invitations'],
      summary: 'Revoke invitation (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'invitationId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: { description: 'Invitation revoked', content: { 'application/json': { schema: { $ref: '#/components/schemas/SuccessResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/invitations/{invitationId}/resend': {
    post: {
      tags: ['Auth', 'Invitations'],
      summary: 'Resend invitation email (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'invitationId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: { description: 'Invitation resent', content: { 'application/json': { schema: { $ref: '#/components/schemas/SuccessResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/auth/activate': {
    post: {
      tags: ['Auth', 'Invitations'],
      summary: 'Activate account from invitation',
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/ActivateAccountRequest' } } },
      },
      responses: {
        201: { description: 'Account activated', content: { 'application/json': { schema: { type: 'object', properties: { success: { type: 'boolean' }, message: { type: 'string' }, data: { type: 'object' } } } } } },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/users': {
    get: {
      tags: ['Users'],
      summary: 'List users (Admin)',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 20, maximum: 100 } },
        { name: 'search', in: 'query', schema: { type: 'string' } },
        { name: 'role', in: 'query', schema: { type: 'string', enum: ['ADMIN', 'FUNDRAISING_STAFF'] } },
        { name: 'isActive', in: 'query', schema: { type: 'boolean' } },
        { name: 'sort', in: 'query', schema: { type: 'string', enum: ['name', 'email', 'role', 'isActive', 'createdAt', 'updatedAt', 'lastLoginAt'] } },
        { name: 'order', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'] } },
      ],
      responses: {
        200: {
          description: 'User list',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      users: { type: 'array', items: { $ref: '#/components/schemas/User' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/users/{userId}': {
    get: {
      tags: ['Users'],
      summary: 'Get user by ID (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'userId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'User details',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { user: { $ref: '#/components/schemas/User' } } },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    patch: {
      tags: ['Users'],
      summary: 'Update user profile (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'userId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/UpdateUserRequest' } } },
      },
      responses: {
        200: {
          description: 'Updated user',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { user: { $ref: '#/components/schemas/User' } } },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/users/{userId}/role': {
    patch: {
      tags: ['Users'],
      summary: 'Update user role (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'userId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/UpdateUserRoleRequest' } } },
      },
      responses: {
        200: {
          description: 'Role updated',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { user: { $ref: '#/components/schemas/User' } } },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/users/{userId}/status': {
    patch: {
      tags: ['Users'],
      summary: 'Activate or deactivate user (Admin)',
      security: bearerSecurity,
      parameters: [{ name: 'userId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/UpdateUserStatusRequest' } } },
      },
      responses: {
        200: {
          description: 'Status updated',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { user: { $ref: '#/components/schemas/User' } } },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Admin only', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies': {
    get: {
      tags: ['Companies'],
      summary: 'List companies with search, filters, and pagination',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1, minimum: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 20, minimum: 1, maximum: 100 } },
        { name: 'search', in: 'query', schema: { type: 'string' }, description: 'Case-insensitive company name search' },
        { name: 'latestFinancialYear', in: 'query', schema: { type: 'string' } },
        { name: 'state', in: 'query', schema: { type: 'string' } },
        { name: 'csrSector', in: 'query', schema: { type: 'string' } },
        { name: 'sortBy', in: 'query', schema: { type: 'string', enum: companySortFields, default: 'company_name' } },
        { name: 'sortOrder', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'], default: 'desc' } },
      ],
      responses: {
        200: {
          description: 'Company list',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      companies: { type: 'array', items: { $ref: '#/components/schemas/Company' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        400: { description: 'Invalid query parameters', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies/{companyId}': {
    get: {
      tags: ['Companies'],
      summary: 'Get company by ID',
      security: bearerSecurity,
      parameters: [{ name: 'companyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Company details',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { company: { $ref: '#/components/schemas/Company' } } },
                },
              },
            },
          },
        },
        400: { description: 'Invalid company ID', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies/{companyId}/summary': {
    get: {
      tags: ['Companies'],
      summary: 'Get concise company WASH summary',
      security: bearerSecurity,
      parameters: [{ name: 'companyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Company summary',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { summary: { $ref: '#/components/schemas/CompanySummary' } } },
                },
              },
            },
          },
        },
        400: { description: 'Invalid company ID', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies/{companyId}/csr': {
    get: {
      tags: ['CSR'],
      summary: 'Get CSR overview for a company',
      security: bearerSecurity,
      parameters: [{ name: 'companyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'CSR overview',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/CSROverview' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies/{companyId}/csr/policies': {
    get: {
      tags: ['CSR'],
      summary: 'List CSR policies for a company',
      security: bearerSecurity,
      parameters: [
        { name: 'companyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } },
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 10, maximum: 100 } },
        { name: 'financialYear', in: 'query', schema: { type: 'string' } },
        { name: 'sort', in: 'query', schema: { type: 'string', enum: ['financialYear', 'title', 'retrievedAt', 'createdAt'] } },
        { name: 'order', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'], default: 'desc' } },
      ],
      responses: {
        200: {
          description: 'Policy list',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      policies: { type: 'array', items: { $ref: '#/components/schemas/CSRPolicy' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies/{companyId}/csr/policies/{policyId}': {
    get: {
      tags: ['CSR'],
      summary: 'Get CSR policy by ID',
      security: bearerSecurity,
      parameters: [
        { name: 'companyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } },
        { name: 'policyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } },
      ],
      responses: {
        200: {
          description: 'Policy details',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { policy: { $ref: '#/components/schemas/CSRPolicy' } } },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Policy not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/companies/{companyId}/sources': {
    get: {
      tags: ['CSR'],
      summary: 'List source references for a company',
      security: bearerSecurity,
      parameters: [
        { name: 'companyId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } },
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 10, maximum: 100 } },
        { name: 'sourceType', in: 'query', schema: { type: 'string' } },
        { name: 'sort', in: 'query', schema: { type: 'string', enum: ['sourceType', 'sourceName', 'retrievedAt', 'createdAt'] } },
        { name: 'order', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'], default: 'desc' } },
      ],
      responses: {
        200: {
          description: 'Source list',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      sources: { type: 'array', items: { $ref: '#/components/schemas/Source' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Company not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/leads': {
    post: {
      tags: ['Leads'],
      summary: 'Create a donor lead',
      security: bearerSecurity,
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/CreateLeadRequest' } } },
      },
      responses: {
        201: {
          description: 'Lead created',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/Lead' },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        409: { description: 'Active lead already exists for company', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    get: {
      tags: ['Leads'],
      summary: 'List leads',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 20, maximum: 100 } },
        { name: 'status', in: 'query', schema: { type: 'string', enum: ['NEW', 'CONTACTED', 'FOLLOW_UP', 'PROPOSAL_SENT', 'WON', 'LOST'] } },
        { name: 'priority', in: 'query', schema: { type: 'string', enum: ['HIGH', 'MEDIUM', 'LOW'] } },
        { name: 'assignedTo', in: 'query', schema: { type: 'string', format: 'objectId' } },
        { name: 'search', in: 'query', schema: { type: 'string' }, description: 'Search company name' },
        { name: 'sort', in: 'query', schema: { type: 'string', enum: ['createdAt', 'updatedAt', 'status', 'priority'] } },
        { name: 'order', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'] } },
      ],
      responses: {
        200: {
          description: 'Lead list',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      leads: { type: 'array', items: { $ref: '#/components/schemas/Lead' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/leads/{leadId}': {
    get: {
      tags: ['Leads'],
      summary: 'Get lead by ID',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Lead details',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/Lead' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    patch: {
      tags: ['Leads'],
      summary: 'Update lead status, priority, or assignee',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/UpdateLeadRequest' } } },
      },
      responses: {
        200: {
          description: 'Updated lead',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/Lead' },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Forbidden', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    delete: {
      tags: ['Leads'],
      summary: 'Archive lead (sets status to LOST)',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Lead archived',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  message: { type: 'string' },
                  data: { $ref: '#/components/schemas/Lead' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Forbidden', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/leads/{leadId}/assign': {
    patch: {
      tags: ['Leads'],
      summary: 'Assign lead to a user',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/AssignLeadRequest' } } },
      },
      responses: {
        200: {
          description: 'Lead assigned',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/Lead' },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Forbidden', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/leads/{leadId}/notes': {
    post: {
      tags: ['Leads'],
      summary: 'Add note to lead',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/CreateLeadNoteRequest' } } },
      },
      responses: {
        201: {
          description: 'Note created',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { note: { $ref: '#/components/schemas/LeadNote' } } },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Forbidden', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    get: {
      tags: ['Leads'],
      summary: 'List notes for a lead',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Lead notes',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { notes: { type: 'array', items: { $ref: '#/components/schemas/LeadNote' } } } },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/leads/{leadId}/activities': {
    post: {
      tags: ['Leads'],
      summary: 'Log outreach activity on a lead',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      requestBody: {
        required: true,
        content: { 'application/json': { schema: { $ref: '#/components/schemas/CreateLeadActivityRequest' } } },
      },
      responses: {
        201: {
          description: 'Activity logged',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { activity: { $ref: '#/components/schemas/LeadActivity' } } },
                },
              },
            },
          },
        },
        400: { description: 'Validation failed', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        403: { description: 'Forbidden', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
    get: {
      tags: ['Leads'],
      summary: 'List activities for a lead',
      security: bearerSecurity,
      parameters: [{ name: 'leadId', in: 'path', required: true, schema: { type: 'string', format: 'objectId' } }],
      responses: {
        200: {
          description: 'Lead activities',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { type: 'object', properties: { activities: { type: 'array', items: { $ref: '#/components/schemas/LeadActivity' } } } },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
        404: { description: 'Lead not found', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/dashboard/summary': {
    get: {
      tags: ['Dashboard'],
      summary: 'Dashboard aggregate summary',
      security: bearerSecurity,
      responses: {
        200: {
          description: 'Dashboard summary metrics',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: { $ref: '#/components/schemas/DashboardSummary' },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/dashboard/top-prospects': {
    get: {
      tags: ['Dashboard'],
      summary: 'Top active lead prospects',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 10, maximum: 100 } },
      ],
      responses: {
        200: {
          description: 'Top prospects',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      prospects: { type: 'array', items: { $ref: '#/components/schemas/Lead' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/dashboard/recent-leads': {
    get: {
      tags: ['Dashboard'],
      summary: 'Recently created leads',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 10, maximum: 100 } },
      ],
      responses: {
        200: {
          description: 'Recent leads',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      leads: { type: 'array', items: { $ref: '#/components/schemas/Lead' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
  '/api/dashboard/follow-ups': {
    get: {
      tags: ['Dashboard'],
      summary: 'Leads requiring follow-up',
      security: bearerSecurity,
      parameters: [
        { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
        { name: 'limit', in: 'query', schema: { type: 'integer', default: 10, maximum: 100 } },
      ],
      responses: {
        200: {
          description: 'Follow-up leads',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  data: {
                    type: 'object',
                    properties: {
                      leads: { type: 'array', items: { $ref: '#/components/schemas/Lead' } },
                      pagination: { $ref: '#/components/schemas/Pagination' },
                    },
                  },
                },
              },
            },
          },
        },
        401: { description: 'Unauthorized', content: { 'application/json': { schema: { $ref: '#/components/schemas/ErrorResponse' } } } },
      },
    },
  },
};

module.exports = paths;
