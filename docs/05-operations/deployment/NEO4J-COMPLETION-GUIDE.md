# Neo4j Memory MCP - Completion Guide

## Current Status

✅ **MCP Registration**: Neo4j Memory MCP server is fully registered in Codex CLI and VS Code Copilot.

Configuration files:
- `.mcp.json` (Codex CLI)
- `.vscode/mcp.json` (VS Code Copilot)
- `scripts/memory/mcp/wrapper.sh` (wrapper script)
- `scripts/dev/setup_copilot_codex_mcp.py` (setup automation)

⏳ **Pending**: Neo4j backend container startup on your machine.

## Why This Matters

The MCP wrapper is registered and ready, but it cannot function without a running Neo4j instance because:

1. MCP server loads the wrapper script which exports Neo4j connection credentials
2. The wrapper calls `@knowall-ai/mcp-neo4j-agent-memory@0.2.5` with `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` environment variables
3. The package attempts to connect to the Neo4j Bolt port (7687) at startup
4. Without a running container on that port, the MCP server cannot initialize

## Start Neo4j Backend

### Quick Start (One Command)

```bash
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community
```

### Docker Compose (If Available)

```bash
docker compose up -d neo4j
```

### Verify Running

```bash
# Check container status
docker ps | grep bioetl-neo4j

# Expected output:
# bioetl-neo4j   neo4j:5.15-community   "tini -g -- ..." Up (healthy)  0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
```

## Verify MCP Connection

### Check 1: Codex Registration

```bash
codex mcp get neo4j-memory
```

**Expected output:**
```
neo4j-memory:
  Type: command
  Command: scripts/memory/mcp/wrapper.sh
  Status: available
```

### Check 2: Full MCP Diagnostic

```bash
bash scripts/memory/mcp/check.sh
```

This script verifies:
- ✅ Codex CLI availability
- ✅ neo4j-memory registration
- ✅ Wrapper script configuration
- ✅ Neo4j port 7687 connectivity
- ✅ Docker container status
- ✅ Memory file existence
- ✅ Environment variables

### Check 3: Neo4j Browser Access

Once container is running:
- **URL**: http://localhost:7474/browser/
- **Username**: `neo4j`
- **Password**: `bioetl_secure_password`

## Integration with Codex

After Neo4j is running and MCP is verified, you can use it in Codex:

```bash
# Interactive Codex with neo4j-memory available
codex interactive
```

Then ask Codex to:
- Store knowledge in Neo4j
- Query memory via Cypher
- Use graph patterns for complex reasoning

Example Codex prompt:
```
Use the neo4j-memory MCP server to:
1. Create a test node: CREATE (n:TestNode {text: 'Hello Neo4j'}) RETURN n
2. Query it back: MATCH (n:TestNode) RETURN n
3. Store the result in memory for later reference
```

## Environment Variables

If using non-standard credentials or port:

```bash
# Custom password
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/custom-password \
  neo4j:5.15-community

# Update .env or export
export NEO4J_AUTH="neo4j/custom-password"
```

The wrapper script (`wrapper.sh`) will:
1. Source `.env` if present
2. Parse `NEO4J_AUTH` into username/password
3. Use `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` if set explicitly
4. Fall back to `neo4j/bioetl_secure_password` if nothing is configured

## Troubleshooting

### Issue: "Error: connect ECONNREFUSED 127.0.0.1:7687"

Neo4j container is not running.

**Solution:**
```bash
docker start bioetl-neo4j
# OR restart with docker run command above
```

### Issue: "Port 7687 is already allocated"

Another container or process is using the port.

**Solution:**
```bash
# Find what's using 7687
docker ps | grep 7687

# Stop the conflicting container
docker stop <container_id>

# OR use a different port
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7688:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community

# Update MCP wrapper to use new port:
export NEO4J_URI="bolt://localhost:7688"
```

### Issue: "codex mcp get neo4j-memory" shows not available

The MCP server is registered but not responding.

**Solution:**
1. Verify Neo4j is running: `docker ps | grep bioetl-neo4j`
2. Check wrapper script exists: `ls -la scripts/memory/mcp/wrapper.sh`
3. Run verification: `bash scripts/memory/mcp/check.sh`

## Documentation

- **Setup Guide**: [NEO4J-STARTUP-GUIDE.md](./NEO4J-STARTUP-GUIDE.md)
- **Memory Configuration**: [neo4j-memory-setup.md](./neo4j-memory-setup.md)
- **MCP Configuration Details**: See `.env.example` for all Neo4j environment variables

## Next Steps

1. **Start Neo4j**:
   ```bash
   docker run -d --name bioetl-neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/bioetl_secure_password \
     neo4j:5.15-community
   ```

2. **Verify Connection**:
   ```bash
   bash scripts/memory/mcp/check.sh
   ```

3. **Access Neo4j Browser**:
   Open http://localhost:7474/browser/ in your browser

4. **Use in Codex**:
   ```bash
   codex interactive
   ```
   Then use `@neo4j-memory` in your prompts

## Related Issues & References

- Neo4j Docker Hub: https://hub.docker.com/_/neo4j
- Neo4j Documentation: https://neo4j.com/docs/
- MCP Specification: https://modelcontextprotocol.io/
- Project MCP Config: See `setup_copilot_codex_mcp.py` for full automation
