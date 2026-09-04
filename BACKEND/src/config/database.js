const mongoose = require('mongoose');

/**
 * Connect to MongoDB using Mongoose.
 * Connection options favour predictable behaviour in development and production.
 */
async function connectDatabase(uri) {
  const mongoUri = uri || process.env.MONGODB_URI;

  if (!mongoUri) {
    throw new Error('MONGODB_URI is not defined in environment variables');
  }

  mongoose.set('strictQuery', true);

  await mongoose.connect(mongoUri, {
    maxPoolSize: 10,
    serverSelectionTimeoutMS: 5000,
  });

  return mongoose.connection;
}

/**
 * Gracefully close the MongoDB connection.
 */
async function disconnectDatabase() {
  await mongoose.disconnect();
}

module.exports = {
  connectDatabase,
  disconnectDatabase,
};
