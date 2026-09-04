/**
 * Minimal Express app shell — API routes will be added in later modules.
 */
require('dotenv').config();

const express = require('express');

const app = express();

app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'jaldhaara-backend' });
});

module.exports = app;
