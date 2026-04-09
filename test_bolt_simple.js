const http = require('http');

const options = {
  hostname: 'localhost',
  port: 7687,
  path: '/',
  method: 'GET',
  timeout: 10000
};

console.log('Attempting Bolt handshake on localhost:7687...');

const req = http.request(options, (res) => {
  console.log(`[OK] Connected! Status: ${res.statusCode}`);
  process.exit(0);
});

req.on('error', (err) => {
  console.error(`[FAIL] Connection error:`, err.message);
  process.exit(1);
});

req.on('timeout', () => {
  console.error('[FAIL] Connection timeout');
  req.destroy();
  process.exit(1);
});

req.end();
