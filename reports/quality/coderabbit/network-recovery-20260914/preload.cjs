// Task-local transport option only; preserve CodeRabbit URL, headers and protocols.
const NativeWebSocket = globalThis.WebSocket;
globalThis.WebSocket = new Proxy(NativeWebSocket, {
  construct(Target, args) {
    const urlArg = String(args[0]);
    const hostname = (() => {
      try {
        return new URL(urlArg).hostname;
      } catch {
        return '';
      }
    })();
    console.error('CodeRabbit WebSocket pre-connect:', urlArg);
    if (hostname.endsWith('coderabbit.ai') && process.env.HTTPS_PROXY) {
      const next = [...args];
      if (next[1] && typeof next[1] === 'object' && !Array.isArray(next[1])) {
        next[1] = {...next[1], proxy: process.env.HTTPS_PROXY};
      } else {
        next[2] = {...(next[2] || {}), proxy: process.env.HTTPS_PROXY};
      }
      console.error('CodeRabbit WebSocket: explicit temporary proxy', process.env.HTTPS_PROXY);
      return Reflect.construct(Target, next);
    }
    console.error('CodeRabbit WebSocket: fallback without proxy');
    return Reflect.construct(Target, args);
  }
});
