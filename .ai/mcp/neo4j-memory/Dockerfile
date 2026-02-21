FROM python:3.13.8-slim

LABEL io.modelcontextprotocol.server.name="io.github.neo4j-contrib/mcp-neo4j-memory"

WORKDIR /app

RUN pip install --no-cache-dir hatchling

COPY .ai/mcp/neo4j-memory/pyproject.toml /app/

RUN pip install --no-cache-dir fastmcp>=2.0.0 neo4j>=5.26.0

COPY .ai/mcp/neo4j-memory/src/ /app/src/
COPY .ai/mcp/neo4j-memory/README.md /app/

RUN pip install --no-cache-dir -e .

ENV NEO4J_URL="bolt://host.docker.internal:7687"
ENV NEO4J_USERNAME="neo4j"
ENV NEO4J_PASSWORD="password"
ENV NEO4J_DATABASE="neo4j"
ENV NEO4J_TRANSPORT="stdio"
ENV NEO4J_MCP_SERVER_HOST="0.0.0.0"
ENV NEO4J_MCP_SERVER_PORT="8000"

CMD ["mcp-neo4j-memory"]
