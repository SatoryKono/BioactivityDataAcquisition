# Neo4j Memory MCP - Smoke Test

**Status**: MCP fully configured. Backend startup pending.

---

## What This Test Does

Comprehensive validation of the complete Neo4j Memory MCP chain after backend starts:

| Test | Validates |
|------|-----------|
| 1️⃣ Docker Container | `bioetl-neo4j` container is running |
| 2️⃣ Network Ports | Bolt (7687) and HTTP (7474) are open |
| 3️⃣ Wrapper Script | `wrapper.sh` exists and is executable |
| 4️⃣ MCP Registration | `neo4j-memory` is registered in Codex CLI |
| 5️⃣ Environment | Neo4j credentials are properly configured |
| 6️⃣ Connectivity | Cypher queries can execute against Neo4j |
| 7️⃣ Browser UI | Neo4j Browser HTTP endpoint is responsive |

---

## When to Run

**After** you start the Neo4j backend on your machine:

```bash
# 1. Start Neo4j (one-time)
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community

# 2. Wait ~10-15 seconds for startup

# 3. Run smoke test
bash scripts/ai/mcp/check_neo4j_memory.sh
```

---

## Running the Test

### On Your Machine (After Starting Neo4j)

```bash
cd /path/to/BioactivityDataAcquisition
bash scripts/ai/mcp/check_neo4j_memory.sh
```

### Expected Output (Success)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST 1: Docker Container Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Docker CLI available
✓ Container bioetl-neo4j is RUNNING
  bioetl-neo4j neo4j:5.15... Up About a minute ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST 2: Neo4j Ports Accessible
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Bolt port (7687) is open
✓ HTTP port (7474) is open

... (more tests) ...

╔════════════════════════════════════════════╗
║  ✓ ALL CRITICAL TESTS PASSED              ║
║  Neo4j Memory MCP is FULLY OPERATIONAL    ║
╚════════════════════════════════════════════╝

🎉 Next Steps:
  1. Open Neo4j Browser: http://localhost:7474/browser/
  2. Test MCP in Codex: codex interactive
  3. Verify MCP details: codex mcp get neo4j-memory
  4. Run comprehensive check: bash scripts/ai/mcp/check_neo4j_memory.sh
```

### Expected Output (Startup in Progress)

If you run the test while Neo4j is still starting:

```
✗ Bolt port (7687) is NOT accessible
! Neo4j may still be starting (takes 10-15 seconds)
```

**Solution**: Wait 10-15 seconds and re-run. It's normal.

---

## Test Breakdown

### Test 1: Docker Container
- Checks if `docker` CLI is available
- Verifies `bioetl-neo4j` container exists and is running

### Test 2: Network Ports
- Tests if Bolt protocol port (7687) accepts connections
- Tests if HTTP port (7474) accepts connections
- Uses `nc` or `/dev/tcp` for platform-agnostic port checking

### Test 3: Wrapper Script
- Verifies wrapper exists at `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh`
- Checks if script is executable
- Validates script contains MCP package reference
- Confirms environment variable setup

### Test 4: MCP Registration
- Checks if `codex mcp list` includes `neo4j-memory`
- Validates wrapper path in MCP configuration
- Only runs if Codex CLI is available

### Test 5: Environment Configuration
- Checks for `NEO4J_AUTH` or separate `NEO4J_USERNAME`/`NEO4J_PASSWORD`
- Validates `.env` file presence
- Reports what credentials wrapper will use

### Test 6: Neo4j Connectivity
- Executes a simple Cypher query via `docker exec`
- Uses wrapper's configured credentials
- Confirms database is accepting queries

### Test 7: Browser Access
- Queries Neo4j HTTP API endpoint
- Verifies Browser UI is served

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Container is NOT RUNNING"** | Start it: `docker run -d --name bioetl-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/bioetl_secure_password neo4j:5.15-community` |
| **Ports are closed** | Neo4j is starting. Wait 10-15 seconds and re-run test. |
| **"neo4j-memory is NOT registered"** | Register MCP: `uv run python -m scripts.engineering.dev setup-mcp` |
| **Wrapper script not executable** | Fix permissions: `chmod +x scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh` |
| **Cypher query fails** | Check Neo4j logs: `docker logs bioetl-neo4j` |

---

## Related Commands

```bash
# Start Neo4j
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community

# View Neo4j logs (watch startup)
docker logs -f bioetl-neo4j

# Check if container is running
docker ps | grep bioetl-neo4j

# Access Neo4j directly via cypher-shell
docker exec -it bioetl-neo4j cypher-shell -u neo4j -p bioetl_secure_password

# Open Neo4j Browser
open http://localhost:7474/browser/  # macOS
xdg-open http://localhost:7474/browser/  # Linux
start http://localhost:7474/browser/  # Windows PowerShell

# Full MCP diagnostic
bash scripts/ai/mcp/check_neo4j_memory.sh

# Use in Codex
codex mcp get neo4j-memory
codex interactive

# Stop and remove container
docker stop bioetl-neo4j
docker rm bioetl-neo4j
```

---

## What Happens Next (After Test Passes)

1. **MCP is ready to use**
   ```bash
   codex interactive
   # Use @neo4j-memory in prompts to access Neo4j from AI
   ```

2. **Neo4j Browser is available**
   - http://localhost:7474/browser/
   - Create test nodes, run Cypher queries
   - Monitor query performance

3. **Wrapper script works**
   - Codex MCP server reads environment variables
   - Connects to Neo4j via `bolt://localhost:7687`
   - Authenticates with configured credentials
   - Handles Neo4j query execution

---

## Files This Test References

| File | Purpose |
|------|---------|
| `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh` | MCP wrapper (tested) |
| `scripts/engineering/dev/setup_copilot_codex_mcp.py` | MCP setup automation (not tested) |
| `.vscode/mcp.json` | VS Code Copilot config (not tested) |
| `.env` or `.env.example` | Credentials source (checked) |
| `docker-compose.yml` | Optional (alternative startup) |

---

## Notes

- **Idempotent**: Safe to run multiple times
- **Platform-agnostic**: Uses `bash`, Docker CLI, and standard utilities (no heavy dependencies)
- **Fast**: Should complete in 5-10 seconds once Neo4j is running
- **Detailed output**: Shows what passes and what fails with remediation hints

---

**Status After Test Passes**: ✅ Neo4j Memory MCP fully operational

See [NEO4J-MCP-INDEX.md](../../deployment/NEO4J-MCP-INDEX.md) for more documentation.
