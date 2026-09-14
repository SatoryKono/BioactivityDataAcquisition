const socket = new WebSocket('wss://ide.coderabbit.ai/ws', {proxy: process.env.HTTPS_PROXY});
await new Promise((resolve, reject) => {
  const timer = setTimeout(() => {socket.close(); reject(new Error('WebSocket timed out'));}, 12000);
  socket.addEventListener('open', () => {clearTimeout(timer); console.error('Explicit-proxy WebSocket OPEN'); socket.close(); resolve();});
  socket.addEventListener('error', (event) => {console.error(event.message); clearTimeout(timer); reject(new Error('WebSocket connection failed'));});
});
