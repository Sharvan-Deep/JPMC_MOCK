const mongoose = require('mongoose');

/**
 * Strict MongoDB ObjectId validation.
 */
function isValidObjectId(id) {
  if (!id || typeof id !== 'string') {
    return false;
  }

  return mongoose.Types.ObjectId.isValid(id) && String(new mongoose.Types.ObjectId(id)) === id;
}

module.exports = {
  isValidObjectId,
};
