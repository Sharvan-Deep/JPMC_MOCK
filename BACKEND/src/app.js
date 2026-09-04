/**
 * Express application — API routes are registered per module.
 */
require('dotenv').config();

const express = require('express');
const cookieParser = require('cookie-parser');
const cors = require('cors');
const authRoutes = require('./routes/authRoutes');
const leadRoutes = require('./routes/leadRoutes');
const dashboardRoutes = require('./routes/dashboardRoutes');
const userRoutes = require('./routes/userRoutes');
const companyRoutes = require('./routes/companyRoutes');
const csrRoutes = require('./routes/csrRoutes');
const { outreachRouter, aiHealthHandler } = require('./routes/outreachRoutes');
const errorHandler = require('./middleware/errorHandler');
const requireAuth = require('./middleware/requireAuth');
const requireRole = require('./middleware/requireRole');
const { USER_ROLES } = require('./config/constants');
const { getCorsOptions } = require('./config/cors');
const swaggerUi = require('swagger-ui-express');
const { openApiSpec } = require('./config/swagger');

const app = express();

app.use(cors(getCorsOptions()));
app.use(cookieParser());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'jaldhaara-backend' });
});

app.get('/api-docs.json', (_req, res) => {
  res.json(openApiSpec);
});

app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(openApiSpec));

app.use('/api/auth', authRoutes);
app.use('/api/leads', leadRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/users', userRoutes);
app.use('/api/companies', companyRoutes);
app.use('/api/companies/:companyId', csrRoutes);
app.use('/api/outreach', outreachRouter);
app.get(
  '/api/ai/health',
  requireAuth,
  requireRole(USER_ROLES.ADMIN, USER_ROLES.FUNDRAISING_STAFF),
  aiHealthHandler
);

app.use(errorHandler);

module.exports = app;
