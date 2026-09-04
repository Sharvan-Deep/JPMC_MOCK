/**
 * Server entry point — starts HTTP server after DB connection.
 * Full API routes are added in subsequent modules.
 */
require('dotenv').config();

const app = require('./app');
const { connectDatabase } = require('./config/database');

const PORT = process.env.PORT || 5000;

async function start() {
  await connectDatabase();
  console.log('MongoDB connected');

  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

start().catch((err) => {
  console.error('Failed to start server:', err.message);
  process.exit(1);
});
