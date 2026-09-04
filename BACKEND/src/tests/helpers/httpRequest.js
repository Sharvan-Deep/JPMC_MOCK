const http = require('http');

/**
 * One-shot HTTP request against a random port of the Express app.
 */
function requestApp(app, path, options = {}) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, () => {
      const { port } = server.address();
      const headers = { ...(options.headers || {}) };
      const payload = options.body !== undefined ? JSON.stringify(options.body) : null;

      if (payload && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }

      if (payload) {
        headers['Content-Length'] = Buffer.byteLength(payload);
      }

      const req = http.request(
        {
          hostname: '127.0.0.1',
          port,
          path,
          method: options.method || 'GET',
          headers,
        },
        (res) => {
          const chunks = [];
          res.on('data', (chunk) => chunks.push(chunk));
          res.on('end', () => {
            server.close();
            const body = Buffer.concat(chunks).toString('utf8');
            let json = null;
            try {
              json = body ? JSON.parse(body) : null;
            } catch {
              json = null;
            }
            resolve({
              status: res.statusCode,
              body,
              json,
            });
          });
        }
      );

      req.on('error', (err) => {
        server.close();
        reject(err);
      });

      if (payload) {
        req.write(payload);
      }

      req.end();
    });
  });
}

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

function installFetchMock(handler) {
  const previous = globalThis.fetch;
  const calls = [];

  globalThis.fetch = async (url, options = {}) => {
    const entry = { url: String(url), method: options.method || 'GET', options };
    calls.push(entry);
    return handler(entry, calls);
  };

  return {
    calls,
    restore() {
      globalThis.fetch = previous;
    },
  };
}

module.exports = {
  requestApp,
  jsonResponse,
  installFetchMock,
};
