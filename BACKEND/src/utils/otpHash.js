const crypto = require('crypto');

/**
 * Hash an OTP before storing in MongoDB.
 * Uses HMAC-SHA256 with a server-side secret — never store raw OTP values.
 */
function hashOTP(otp, secret) {
  const key = secret || process.env.OTP_HASH_SECRET;
  if (!key) {
    throw new Error('OTP_HASH_SECRET is not defined');
  }

  return crypto.createHmac('sha256', key).update(String(otp)).digest('hex');
}

/**
 * Constant-time comparison to prevent timing attacks during OTP verification.
 */
function verifyOTP(otp, otpHash, secret) {
  const computed = hashOTP(otp, secret);
  const a = Buffer.from(computed, 'hex');
  const b = Buffer.from(otpHash, 'hex');

  if (a.length !== b.length) {
    return false;
  }

  return crypto.timingSafeEqual(a, b);
}

module.exports = {
  hashOTP,
  verifyOTP,
};
