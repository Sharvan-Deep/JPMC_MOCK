/**
 * Express application — API routes are registered per module.
 */
require('dotenv').config();

const express = require('express');
const companyRoutes = require('./routes/companyRoutes');
const errorHandler = require('./middleware/errorHandler');

const app = express();

app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'jaldhaara-backend' });
});

app.use('/api/companies', companyRoutes);

app.use(errorHandler);

module.exports = app;
