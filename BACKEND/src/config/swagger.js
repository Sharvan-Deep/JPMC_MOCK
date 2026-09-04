const { schemas } = require('./swagger/schemas');
const paths = require('./swagger/paths');
const aiPaths = require('./swagger/aiPaths');

/**
 * OpenAPI 3.x specification for the Jaldhaara backend API.
 */
function buildOpenApiSpec() {
  const port = process.env.PORT || 5000;

  return {
    openapi: '3.0.3',
    info: {
      title: 'Jaldhaara Foundation API',
      version: '1.0.0',
      description:
        'REST API for Jaldhaara donor discovery and fundraising operations. ' +
        'Protected endpoints require a JWT access token via `Authorization: Bearer <token>`. ' +
        'Login also sets an httpOnly `refreshToken` cookie for `/api/auth/refresh` and `/api/auth/logout`.',
    },
    servers: [
      {
        url: `http://localhost:${port}`,
        description: 'Local development',
      },
    ],
    tags: [
      { name: 'System' },
      { name: 'Auth' },
      { name: 'Invitations' },
      { name: 'Users' },
      { name: 'Companies' },
      { name: 'CSR' },
      { name: 'Leads' },
      { name: 'Dashboard' },
      { name: 'AI' },
      { name: 'Outreach' },
    ],
    paths: {
      ...paths,
      ...aiPaths,
    },
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
          description: 'JWT access token from POST /api/auth/login',
        },
      },
      schemas,
    },
  };
}

const openApiSpec = buildOpenApiSpec();

module.exports = {
  buildOpenApiSpec,
  openApiSpec,
};
