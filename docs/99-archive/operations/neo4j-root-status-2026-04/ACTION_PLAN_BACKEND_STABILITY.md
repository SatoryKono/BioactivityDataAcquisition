# Neo4j Backend Instability - Action Plan

**Status**: Backend flapping - MCP config is correct, infrastructure unstable

**Safety**: Do NOT write data until stability confirmed

---

## What We Know

✅ **MCP Configuration** - All correct
- Wrapper loads environment properly
- Codex registration working
- Package @knowall-ai/mcp-neo4j-agent-memory ready

❌ **Backend Stability** - Flapping
- One HTTP probe succeeded (200 OK)
- Subsequent requests timeout
- Bolt protocol consistently times out
- Docker daemon commands themselves hanging

---

## Root Cause

**Not** MCP or Neo4j configuration issues.

**Is** one of:
1. Docker Desktop WSL2 networking unstable (most likely)
2. Docker daemon resource exhaustion
3. WSL2 network stack issue

---

## What To Do Next (On Your Machine)

### Step 1: Diagnose Docker Desktop
1. Open Docker Desktop Dashboard
2. Check **Stats** tab for:
   - CPU usage (should be normal, not 100%)
   - Memory (should have headroom)
   - Disk I/O (should not be maxed)
3. Screenshot if abnormal

### Step 2: Restart Docker Desktop
1. Right-click Docker icon → **Restart**
2. Wait 2-3 minutes for full startup
3. Verify: `docker ps` (should respond quickly)

### Step 3: Restart Neo4j Container
```bash
docker stop bioetl-neo4j
docker rm -f bioetl-neo4j
bash scripts/ops/wsl_neo4j_startup.sh
```

### Step 4: Test Stability
```bash
# Quick health check
docker ps | Select-String neo4j
docker exec bioetl-neo4j cypher-shell -u neo4j -p bioetl_secure_password "RETURN 1"

# Extended test
bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh
```

---

## If Problem Persists

**Try lower memory settings**:

Edit `scripts/ops/wsl_neo4j_startup.sh`:

Find these lines:
```bash
-e NEO4J_server_memory_heap_max_size=512m \
-e NEO4J_server_memory_pagecache_size=256m \
```

Change to:
```bash
-e NEO4J_server_memory_heap_max_size=256m \
-e NEO4J_server_memory_pagecache_size=128m \
```

Then retry startup.

---

## If Still Unstable

**Nuclear option - full reset**:

```powershell
# Windows PowerShell
docker stop bioetl-neo4j
docker rm -f bioetl-neo4j
wsl --shutdown
# Restart Docker Desktop
# Then from WSL bash:
bash scripts/ops/wsl_neo4j_startup.sh
```

---

## Prepared Files (When Backend Stable)

Once backend stabilizes:
- `/tmp/seed_test_docs_memory.js` (ready for seeding)
- `/tmp/query_test_docs_memory.js` (ready for testing)

Can be loaded when Docker is healthy.

---

## Session Summary

**Completed**: MCP configuration ✅
- Wrapper: correct ✓
- Environment loading: correct ✓
- Codex registration: correct ✓
- Documentation: complete ✓

**Blocked**: Backend stability ❌
- Container intermittent
- Bolt/HTTP both timing out
- Docker daemon hanging

**Next**: Diagnose and fix Docker Desktop / WSL networking

---

**Status**: Infrastructure issue, not MCP issue
**Action**: Restart Docker Desktop, retest
**Safety**: Don't write to Neo4j until stable

