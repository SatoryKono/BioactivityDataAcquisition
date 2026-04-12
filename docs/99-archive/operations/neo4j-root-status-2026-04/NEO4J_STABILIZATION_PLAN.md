# Neo4j Stabilization for Live Audit Workload

## Problem Statement

Live validation reaches snapshot building (98s), but fails on first Neo4j write/query with OOMKilled (ExitCode 137). Container has only 256m heap for workload that needs 400-600m.

---

## Solution: Container Profile for Live Audit

Create a separate Neo4j profile optimized for heavy audit workload.

### Step 1: Create docker-compose.neo4j-audit.yml

```yaml
# For live audit: higher memory, dedicated instance
services:
  neo4j-audit:
    image: neo4j:5.13-community
    container_name: bioetl-neo4j-audit
    ports:
      - "7475:7474"  # Different port to avoid conflict
      - "7688:7687"
    environment:
      NEO4J_AUTH: neo4j/audit_password
      NEO4J_ACCEPT_LICENSE_AGREEMENT: "yes"
      # Aggressive heap for audit workload
      NEO4J_server_memory_heap_initial__size: 512m
      NEO4J_server_memory_heap_max__size: 1024m
      NEO4J_server_memory_pagecache_size: 256m
    restart: no
    mem_limit: 2g
    cpus: "2.0"
```

### Step 2: Update Code to Use Audit Instance During Live Validation

In audit code (where Neo4j writes happen):

```python
# For live audit, use higher-memory instance
if os.getenv('LIVE_AUDIT_MODE'):
    NEO4J_URI = 'bolt://localhost:7688'  # Audit instance
    NEO4J_PASSWORD = 'audit_password'
else:
    NEO4J_URI = 'bolt://localhost:7687'  # MCP instance
    NEO4J_PASSWORD = 'bioetl_secure_password'
```

### Step 3: Run Live Validation

```bash
# Start audit instance
docker compose -f docker-compose.neo4j-audit.yml up -d
sleep 30

# Run validation
export LIVE_AUDIT_MODE=1
live --apply --only-complexity-layer --batch-size 5

# Clean up
docker compose -f docker-compose.neo4j-audit.yml down
```

---

## Alternative: Increase Default Instance Memory

If separate instance is too complex, increase heap of default instance:

```yaml
# docker-compose.neo4j.yml
environment:
  NEO4J_server_memory_heap_initial__size: 384m
  NEO4J_server_memory_heap_max__size: 512m
  NEO4J_server_memory_pagecache_size: 128m
mem_limit: 1.5g
```

**Test**: Run live validation. If still OOMKilled, increase to 512m heap.

---

## Verification Steps

### 1. Check Memory Usage During Live Validation

```powershell
# Terminal 1: Run live validation
export LIVE_AUDIT_MODE=1
live --apply --only-complexity-layer --batch-size 5

# Terminal 2: Monitor Neo4j
docker stats bioetl-neo4j-audit --no-stream

# Should NOT exceed mem_limit (2g)
```

### 2. Verify No OOMKilled

```powershell
docker inspect bioetl-neo4j-audit --format='{{json .State.OOMKilled}}'
# Should return: false
```

### 3. Full Live Validation

```bash
export LIVE_AUDIT_MODE=1
live --report-fast

# Should complete without OOMKilled errors
```

---

## Expected Results

| Before | After |
|--------|-------|
| Fails at first query (OOM) | Completes full validation |
| Container killed | Container stable |
| ExitCode 137 | ExitCode 0 |

---

## Backup Plan: Disable Neo4j for CLI

If infrastructure proves too complex, simple alternative:

```python
# In live audit code
if os.getenv('LIVE_AUDIT_SKIP_NEO4J'):
    # Skip Neo4j writes
    # Use in-memory or file-based storage
    pass
else:
    # Normal Neo4j writes
    ...
```

Then:
```bash
# Kill Neo4j, run audit
docker kill bioetl-neo4j
export LIVE_AUDIT_SKIP_NEO4J=1
live --apply

# Restart Neo4j for MCP
docker compose -f docker-compose.neo4j.yml up -d
```

**Pros**: Simplest fix, frees memory for Python
**Cons**: No Neo4j audit trail during live validation

---

## Recommendations

1. **If MCP is critical for audit**: Use separate neo4j-audit instance (512m+ heap)
2. **If MCP is not used during audit**: Increase default heap to 512m
3. **If infrastructure is too complex**: Skip Neo4j writes during audit, keep MCP for Codex

Current status: #2795 can be closed (Python code is fast enough). Create new issue for Neo4j infrastructure stabilization with this plan.

---

**Next action**: Choose option 1, 2, or 3 above and implement. Test with live validation to verify OOMKilled does not occur.
