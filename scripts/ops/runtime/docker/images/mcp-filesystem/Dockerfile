# BioETL MCP Filesystem Server - Secure filesystem access for AI agents
FROM node:22-alpine

WORKDIR /app

# Install dependencies once, cache node_modules
RUN npm install --production --no-fund @modelcontextprotocol/server-filesystem@2026.1.14

# Non-root user
RUN addgroup mcpuser && adduser -D -G mcpuser mcpuser
USER mcpuser

# Default to project root; override via ENTRYPOINT args
ENTRYPOINT ["npx", "@modelcontextprotocol/server-filesystem@2026.1.14"]
CMD ["/app"]
