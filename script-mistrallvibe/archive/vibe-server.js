#!/usr/bin/env node
/**
 * Mistral Vibe Server
 * Simple Node.js server for Mistral API proxy
 */

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');
const url = require('node:url');

// Configuration
const PORT = process.env.VIBE_PORT || 5173;
const API_KEY = process.env.VIBE_API_KEY || '';
const MISTRAL_API_URL = 'https://api.mistral.ai/v1';

if (!API_KEY) {
    console.error('[ERROR] VIBE_API_KEY environment variable not set');
    console.error('Set it in .env.mistrallvibe or export VIBE_API_KEY=your-key');
    process.exit(1);
}

console.log(`[INFO] Starting Mistral Vibe Server`);
console.log(`[INFO] Port: ${PORT}`);
console.log(`[INFO] API Key: ${API_KEY.substring(0, 10)}...${API_KEY.substring(API_KEY.length - 10)}`);

// Read HTML file
const htmlPath = path.join(__dirname, 'vibe-ui.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

// Create server
const server = http.createServer((req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;

    // Routes
    if (pathname === '/' && req.method === 'GET') {
        // Serve HTML
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(htmlContent);
    } else if (pathname === '/api/status' && req.method === 'GET') {
        // Check API status
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', api_key_set: !!API_KEY }));
    } else if (pathname === '/api/chat' && req.method === 'POST') {
        // Chat endpoint
        handleChat(req, res);
    } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not found' }));
    }
});

// Handle chat requests
function handleChat(req, res) {
    let body = '';

    req.on('data', chunk => {
        body += chunk.toString();
    });

    req.on('end', async () => {
        try {
            const data = JSON.parse(body);
            const { model, messages, temperature, max_tokens } = data;

            if (!model || !messages) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Missing model or messages' }));
                return;
            }

            // Call Mistral API
            const apiRequest = https.request(
                new URL(`${MISTRAL_API_URL}/chat/completions`),
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${API_KEY}`,
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                },
                (apiRes) => {
                    let apiBody = '';

                    apiRes.on('data', chunk => {
                        apiBody += chunk.toString();
                    });

                    apiRes.on('end', () => {
                        try {
                            const apiData = JSON.parse(apiBody);

                            if (apiRes.statusCode !== 200) {
                                console.error('[API ERROR]', apiData);
                                res.writeHead(apiRes.statusCode, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ error: apiData.error?.message || 'API error' }));
                                return;
                            }

                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify(apiData));
                        } catch (e) {
                            console.error('[PARSE ERROR]', e.message);
                            res.writeHead(500, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ error: 'Failed to parse API response' }));
                        }
                    });
                }
            );

            apiRequest.on('error', (e) => {
                console.error('[REQUEST ERROR]', e.message);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'API request failed: ' + e.message }));
            });

            const requestPayload = {
                model,
                messages,
                temperature: temperature || 0.7,
                max_tokens: max_tokens || 1024
            };

            apiRequest.write(JSON.stringify(requestPayload));
            apiRequest.end();
        } catch (e) {
            console.error('[ERROR]', e.message);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid request: ' + e.message }));
        }
    });
}

// Start server
server.listen(PORT, () => {
    console.log(`[OK] Server running on http://localhost:${PORT}`);
    console.log(`[INFO] Open http://localhost:${PORT} in your browser`);
});

// Handle errors
server.on('error', (e) => {
    console.error('[ERROR]', e.message);
    process.exit(1);
});
