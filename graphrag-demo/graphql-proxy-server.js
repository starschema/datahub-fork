const http = require('http');
const fs = require('fs');

const DATAHUB_URL = 'http://localhost:8080/api/graphql';

const server = http.createServer(async (req, res) => {
  // Serve HTML file
  if (req.url === '/' || req.url === '/index.html') {
    fs.readFile('graphql-client.html', (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading page');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }

  // Proxy GraphQL requests
  if (req.url === '/graphql' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      const options = {
        hostname: 'localhost',
        port: 8080,
        path: '/api/graphql',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body)
        }
      };

      const proxyReq = http.request(options, (proxyRes) => {
        let data = '';
        proxyRes.on('data', chunk => data += chunk);
        proxyRes.on('end', () => {
          res.writeHead(proxyRes.statusCode, { 'Content-Type': 'application/json' });
          res.end(data);
        });
      });

      proxyReq.on('error', (err) => {
        console.error('Proxy error:', err);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      });

      proxyReq.write(body);
      proxyReq.end();
    });
    return;
  }

  // 404 for other routes
  res.writeHead(404);
  res.end('Not Found');
});

const PORT = 7777;
server.listen(PORT, () => {
  console.log(`GraphQL Proxy Server running at http://localhost:${PORT}`);
  console.log(`Proxying requests to ${DATAHUB_URL}`);
});
