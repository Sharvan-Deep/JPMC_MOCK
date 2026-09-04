/**
 * Swagger / OpenAPI smoke tests (no MongoDB required).
 */
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const app = require('../app');
const { openApiSpec } = require('../config/swagger');

function request(path) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, () => {
      const { port } = server.address();

      http
        .get(`http://127.0.0.1:${port}${path}`, (res) => {
          const chunks = [];

          res.on('data', (chunk) => chunks.push(chunk));
          res.on('end', () => {
            server.close();
            resolve({
              status: res.statusCode,
              headers: res.headers,
              body: Buffer.concat(chunks).toString('utf8'),
            });
          });
        })
        .on('error', (err) => {
          server.close();
          reject(err);
        });
    });
  });
}

function countDocumentedOperations(spec) {
  return Object.values(spec.paths).reduce((total, pathItem) => {
    return total + Object.keys(pathItem).length;
  }, 0);
}

describe('Swagger documentation', () => {
  it('GET /api-docs returns Swagger UI HTML', async () => {
    const res = await request('/api-docs/');

    assert.equal(res.status, 200);
    assert.match(res.headers['content-type'], /text\/html/);
    assert.match(res.body, /swagger-ui/i);
  });

  it('GET /api-docs.json returns valid OpenAPI document', async () => {
    const res = await request('/api-docs.json');

    assert.equal(res.status, 200);
    assert.match(res.headers['content-type'], /application\/json/);

    const doc = JSON.parse(res.body);
    assert.equal(doc.openapi, '3.0.3');
    assert.ok(doc.paths['/api/auth/login']);
    assert.ok(doc.paths['/api/companies']);
    assert.ok(doc.paths['/api/leads']);
    assert.ok(doc.paths['/api/dashboard/summary']);
    assert.ok(doc.paths['/api/companies/{companyId}/analyze']);
    assert.ok(doc.paths['/api/leads/{leadId}/score']);
    assert.ok(doc.paths['/api/outreach/{id}/send']);
    assert.ok(doc.components.securitySchemes.bearerAuth);
  });

  it('OpenAPI spec includes representative protected and public endpoints', () => {
    assert.ok(openApiSpec.paths['/api/auth/login'].post);
    assert.ok(openApiSpec.paths['/api/auth/me'].get.security);
    assert.ok(openApiSpec.paths['/api/companies/{companyId}/csr'].get.security);
    assert.ok(openApiSpec.paths['/api/leads'].get.security);
    assert.ok(openApiSpec.paths['/api/companies/{companyId}/analyze'].post.security);
    assert.ok(openApiSpec.paths['/api/leads/top'].get.security);
    assert.ok(openApiSpec.paths['/api/outreach/{id}/approve'].post.security);
    assert.ok(!openApiSpec.paths['/api/v1/scoring/score']);
    assert.ok(!openApiSpec.paths['/api/auth/forgot-password'].post.security);
    assert.ok(!openApiSpec.paths['/api/auth/activate'].post.security);
  });

  it('documents expected number of API operations', () => {
    const operationCount = countDocumentedOperations(openApiSpec);
    assert.ok(operationCount >= 40, `expected at least 40 operations, got ${operationCount}`);
  });
});
