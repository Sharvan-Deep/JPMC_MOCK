const crypto = require('crypto');

/**
 * Unique suffix for one test-file run so fixtures never collide with
 * development data (e.g. admin@jaldhaara.com) and can be cleaned up by filter.
 */
function createTestRun() {
  const id = `${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
  const escapedId = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const emailPattern = new RegExp(`\\.${escapedId}@jaldhaara\\.test$`);

  return {
    id,
    email(localPart) {
      return `${localPart}.${id}@jaldhaara.test`;
    },
    emailFilter() {
      return { email: emailPattern };
    },
  };
}

module.exports = {
  createTestRun,
};
