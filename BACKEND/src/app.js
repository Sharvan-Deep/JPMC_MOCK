/**
 * Minimal Express app shell — API routes are registered per module.
 */
require('dotenv').config();

const express = require('express');
const cookieParser = require('cookie-parser');
const cors = require('cors');
const authRoutes = require('./routes/authRoutes');
const leadRoutes = require('./routes/leadRoutes');
const errorHandler = require('./middleware/errorHandler');
const { getCorsOptions } = require('./config/cors');

const app = express();

app.use(cors(getCorsOptions()));
app.use(cookieParser());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'jaldhaara-backend' });
});

app.use('/api/auth', authRoutes);
app.use('/api/leads', leadRoutes);

app.use(errorHandler);

module.exports = app;
