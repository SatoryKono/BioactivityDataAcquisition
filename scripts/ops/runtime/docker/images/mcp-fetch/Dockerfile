# BioETL MCP Fetch Server - Fast HTTP fetching for AI agents
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install mcp-server-fetch once during build (not at runtime)
RUN pip install --no-cache-dir mcp-server-fetch==2025.4.7

# Non-root user for security
RUN useradd -m -u 1000 mcpuser
USER mcpuser

# Run the server
ENTRYPOINT ["mcp-server-fetch"]
