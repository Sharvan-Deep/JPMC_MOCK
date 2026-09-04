/**
 * Python AI service connection settings.
 * Credentials for Gemini/OpenAI/Chroma stay on the AI service, not here.
 */
function getAiConfig() {
  const baseUrl = String(process.env.AI_SERVICE_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const timeoutMs = Number.parseInt(process.env.AI_SERVICE_TIMEOUT_MS, 10);

  return {
    baseUrl,
    timeoutMs: Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 30000,
  };
}

module.exports = {
  getAiConfig,
};
