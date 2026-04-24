---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-12'
---

# Neo4j Audit Instance - Live Validation Setup

## Quick Start

### 1. Start Audit Instance (1024m heap)

```powershell
.\scripts\ops\start-neo4j-audit.ps1
```

**Output**:
```
✅ Audit instance started successfully

Connection details:
  HTTP:  http://localhost:7475
  Bolt:  bolt://localhost:7688
  Auth:  neo4j / audit_secure_password
```

### 2. Run Live Validation

```bash
# Enable audit mode
set LIVE_AUDIT_MODE=1

# Run validation (use audit instance automatically)
live --apply --only-complexity-layer --batch-size 5

# Or full validation
live --report-fast
```

### 3. Stop Audit Instance

```powershell
.\scripts\ops\start-neo4j-audit.ps1 -Stop
```

---

## How It Works

### Separate Instances

| Instance | Purpose | Memory | Port HTTP | Port Bolt | Password |
|----------|---------|--------|-----------|-----------|----------|
| **bioetl-neo4j** | MCP (Codex) | 256m heap | 7474 | 7687 | bioetl_secure_password |
| **bioetl-neo4j-audit** | Live audit | 1024m heap | 7475 | 7688 | audit_secure_password |

### Automatic Routing

When `LIVE_AUDIT_MODE=1` is set:

```python
# In src/tools/neo4j_audit.py
uri = get_neo4j_uri()
# Returns: bolt://localhost:7688 (audit instance)

auth = get_neo4j_auth()
# Returns: ('neo4j', 'audit_secure_password')
```

Code automatically connects to the audit instance.

---

## Configuration

### docker-compose.neo4j-audit.yml

**Memory allocation** (tuned for live audit workload):
```yaml
NEO4J_server_memory_heap_initial__size: 512m    # Initial
NEO4J_server_memory_heap_max__size: 1024m       # Max (4x MCP instance)
NEO4J_server_memory_pagecache_size: 256m        # Page cache
mem_limit: 2g                                    # Container hard limit
cpus: "2.0"                                      # 2 CPU cores
```

**Why**:
- MCP instance: 256m heap (minimal, for conversation memory)
- Audit instance: 1024m heap (aggressive, for heavy graph operations)
- Separate instances prevent resource contention

### src/tools/neo4j_audit.py

Helper functions:
```python
# Get URI for current context
uri = get_neo4j_uri()

# Get auth for current context
username, password = get_neo4j_auth()

# Check if audit mode
if is_audit_mode():
    print("Running in audit mode (high memory)")
```

---

## Usage in Code

### Before (hardcoded)
```python
driver = neo4j.driver('bolt://localhost:7687', auth=...)
```

### After (context-aware)
```python
from src.tools.neo4j_audit import get_neo4j_uri, get_neo4j_auth

driver = neo4j.driver(
    get_neo4j_uri(),
    neo4j.auth.basic(*get_neo4j_auth())
)
```

---

## Live Validation Workflow

### Step-by-step

```bash
# 1. Start audit instance (1024m heap)
.\scripts\ops\start-neo4j-audit.ps1
# Wait for: "✅ Audit instance started successfully"

# 2. Enable audit mode
set LIVE_AUDIT_MODE=1

# 3. Run validation (will use audit instance)
live --apply --only-complexity-layer --batch-size 5
# Expected: No OOMKilled, completes successfully

# 4. Check status
docker stats bioetl-neo4j-audit --no-stream
# Should show: Memory usage < 2g limit, no OOMKilled

# 5. View logs (if needed)
.\scripts\ops\start-neo4j-audit.ps1 -Logs

# 6. Stop instance
.\scripts\ops\start-neo4j-audit.ps1 -Stop
```

---

## Expected Results

### Before (OOMKilled)
```
live --report-fast
# ... after 98s snapshot ...
# OOMKilled=true, ExitCode 137
❌ FAIL
```

### After (Successful)
```
set LIVE_AUDIT_MODE=1
live --report-fast
# ... after 98s snapshot ...
# ... completes queries ...
# Container memory: 1.2g / 2g limit
✅ PASS
```

---

## Monitoring

### Real-time Memory Usage

```powershell
# During live validation
docker stats bioetl-neo4j-audit --no-stream --interval 1
```

**Look for**:
- Memory Usage: should peak around 1.5-1.8g
- Should NOT exceed 2g (hard limit)
- CPU: will spike during writes, then drop

### After Completion

```powershell
# Verify no OOMKilled
docker inspect bioetl-neo4j-audit --format='{{json .State.OOMKilled}}'
# Should return: false

# Check exit code
docker inspect bioetl-neo4j-audit --format='{{json .State.ExitCode}}'
# Should return: 0
```

---

## Troubleshooting

### Container Fails to Start

```powershell
# Check logs
.\scripts\ops\start-neo4j-audit.ps1 -Logs

# Common issues:
# - Port 7475 already in use: docker kill bioetl-neo4j
# - Out of memory: Close other applications
# - Image not found: docker pull neo4j:5.13-community
```

### OOMKilled During Audit

```powershell
# Increase heap further (if possible)
# Edit docker-compose.neo4j-audit.yml:
# NEO4J_server_memory_heap_max__size: 1536m  (1.5g)
# mem_limit: 2.5g

# Or reduce batch size
live --apply --batch-size 1
```

### Connection Refused

```bash
# Verify audit instance is running
docker ps | Select-String bioetl-neo4j-audit
# Should show: "Up ... (healthy)"

# Verify LIVE_AUDIT_MODE is set
echo $env:LIVE_AUDIT_MODE
# Should show: 1
```

---

## Two Instances, One Codebase

This setup allows:
- ✅ **Codex (MCP)**: Uses bioetl-neo4j (256m, lightweight)
- ✅ **Live audit**: Uses bioetl-neo4j-audit (1024m, heavy)
- ✅ Both run simultaneously if needed
- ✅ No code changes: just set LIVE_AUDIT_MODE=1

---

## Summary

| Scenario | Instance | Command |
|----------|----------|---------|
| Use @neo4j-memory in Codex | bioetl-neo4j | `docker compose -f docker-compose.neo4j.yml up -d` |
| Run live validation | bioetl-neo4j-audit | `.\scripts\ops\start-neo4j-audit.ps1` |
| Both simultaneously | Both | Start both, set LIVE_AUDIT_MODE for audit code |

---

**Status**: Audit instance ready. Use `start-neo4j-audit.ps1` before running live validation. Expected: No OOMKilled errors.
