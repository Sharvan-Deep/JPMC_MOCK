/**
 * CORS configuration — credentials require explicit origins (no wildcard).
 */

function getCorsOrigins() {
  const raw = process.env.CORS_ORIGINS;

  if (!raw || !raw.trim()) {
    return ['http://localhost:3000'];
  }

  return raw
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);
}

function getCorsOptions() {
  return {
    origin: getCorsOrigins(),
    credentials: true,
  };
}

module.exports = {
  getCorsOrigins,
  getCorsOptions,
};
