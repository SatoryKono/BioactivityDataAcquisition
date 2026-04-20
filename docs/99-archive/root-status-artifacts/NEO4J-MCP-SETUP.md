# Neo4j Memory MCP Server - Fixed Setup

## Status: ✅ RUNNING

Neo4j is now running successfully with the MCP server configured.

### Configuration Changes Made

1. **docker-compose.yml**: Fixed memory configuration
   - Heap Initial: 256m (was 512m)
   - Heap Max: 512m (was 2g)
   - Page Cache: 256m (was 1g)
   - Transaction Max: 512m (was 2g/20g)
   - Removed deprecated settings: `dbms.default_database`, `dbms.memory.transaction.global_max_size`, `dbms.memory.transaction.max_size`
   - Updated to new format: `initial.dbms.default_database`, `db.memory.transaction.max`

2. **`.mcp.json`**: Added `neo4j-cypher` server via the project wrapper
   - Wrapper: `scripts/ops/mcp_neo4j_cypher_wrapper.sh`
   - Secrets come from the local untracked `.env` file
   - Supports either `NEO4J_USERNAME` / `NEO4J_PASSWORD` or `NEO4J_AUTH=user/password`

3. **Created `.env.local`**: Local environment overrides for memory tuning

### Neo4j Connection Details

```
Service: bioetl-neo4j
Status: Healthy ✓
Ports:
  - Bolt: localhost:7687 (binary protocol)
  - HTTP: localhost:7474 (browser UI)
Username: neo4j
Password: bioetl_secure_password
Default Database: neo4j
```

### Access Neo4j

**Browser UI**
- URL: http://localhost:7474
- Username: neo4j
- Password: bioetl_secure_password

**Command Line (if needed)**
```bash
docker exec -it bioetl-neo4j cypher-shell -a bolt://localhost:7687 -u neo4j -p bioetl_secure_password
```

### MCP Server Usage

The `neo4j-cypher` server is now available in your Claude/AI client interface with these capabilities:

- **Execute Cypher Queries**: Run graph queries
- **Database Inspection**: Query schema and structure
- **Transaction Management**: Multi-statement transactions
- **Memory Storage**: Use Neo4j as persistent memory backend

### Example Test Query

Through your AI interface, request:
```
Execute this Cypher query via MCP:
RETURN "Neo4j MCP Server is connected!" as status
```

### Adjusting Memory (if needed)

Edit `docker-compose.yml` in the neo4j service environment section:

```yaml
NEO4J_server_memory_heap_max__size: 512m          # Increase/decrease as needed
NEO4J_server_memory_pagecache_size: 256m          # Adjust cache size
NEO4J_db_memory_transaction_max: 512m             # Per-transaction limit
```

Then restart:
```bash
docker-compose restart neo4j
```

### Verify Service Health

```bash
# Check container status
docker-compose ps neo4j

# View logs
docker-compose logs neo4j

# Test connection
curl http://localhost:7474/browser/

# Health endpoint
curl http://localhost:7474/api/
```

### MCP Reload

**To activate the neo4j-cypher server in Claude/AI client:**
1. Restart your AI client application
2. The MCP server will auto-load from .mcp.json
3. Test by asking: "Can you connect to the Neo4j MCP server?"

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Memory error on startup | Increase system RAM or reduce heap sizes in docker-compose.yml |
| Connection refused | Verify `docker-compose ps` shows healthy status |
| Password not accepted | Confirm password in `.env` matches docker-compose.yml `NEO4J_AUTH` value |
| MCP not available | Restart your AI client; check `.mcp.json` syntax with `jq .` and ensure the wrapper can read `.env` |

---

**Last Updated**: 2026-04-08
**Neo4j Version**: 5.15-community
**Memory Footprint**: ~1GB total (256m heap + 256m cache)
