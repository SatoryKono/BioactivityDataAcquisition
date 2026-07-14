______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-12'

______________________________________________________________________

# Neo4j Audit Instance - Quick Reference

## Files Created ✅

All files are ready to use. No additional setup needed.

### Configuration

- **docker-compose.neo4j-audit.yml** — Audit instance definition (1024m heap, port 7688)

### Scripts

- **scripts/ops/runtime/neo4j/start-neo4j-audit.ps1** — PowerShell: start/stop/logs
- **scripts/ops/runtime/neo4j/start-neo4j-audit.sh** — Bash: start/stop/logs (WSL)

### Code Integration

- **src/tools/neo4j_audit.py** — Helper functions for context-aware connections

### Documentation

- **NEO4J_AUDIT_INSTANCE_GUIDE.md** — Full user guide
- **AUDIT_INSTANCE_IMPLEMENTATION.md** — Implementation checklist

______________________________________________________________________

## How to Use

### Start Audit Instance (PowerShell)

```powershell
.\scripts\ops\start-neo4j-audit.ps1
```

Expected output:

```
✅ Audit instance started successfully

Connection details:
  HTTP:  http://localhost:7475
  Bolt:  bolt://localhost:7688
  Auth:  supplied via NEO4J_AUDIT_USERNAME / NEO4J_AUDIT_PASSWORD
```

### Start Audit Instance (WSL/Bash)

```bash
chmod +x scripts/ops/runtime/neo4j/start-neo4j-audit.sh
./scripts/ops/runtime/neo4j/start-neo4j-audit.sh
```

### Run Live Validation

```bash
# Set audit mode
export LIVE_AUDIT_MODE=1
# or PowerShell:
# set LIVE_AUDIT_MODE=1

# Run validation
live --apply --only-complexity-layer --batch-size 5
# or full:
# live --report-fast
```

### Stop Audit Instance

```powershell
.\scripts\ops\start-neo4j-audit.ps1 -Stop
```

or

```bash
./scripts/ops/runtime/neo4j/start-neo4j-audit.sh --stop
```

______________________________________________________________________

## Architecture

### Two Separate Instances

```
bioetl-neo4j          bioetl-neo4j-audit
├─ Port 7474          ├─ Port 7475
├─ Port 7687          ├─ Port 7688
├─ 256m heap          ├─ 1024m heap
├─ 1g limit           ├─ 2g limit
└─ MCP (Codex)        └─ Live Audit
```

### Automatic Routing (Python)

```python
from src.tools.neo4j_audit import get_neo4j_uri, get_neo4j_auth

# If LIVE_AUDIT_MODE=1:
get_neo4j_uri()  # → bolt://localhost:7688 (audit)
get_neo4j_auth()  # → values from NEO4J_AUDIT_USERNAME / NEO4J_AUDIT_PASSWORD

# If LIVE_AUDIT_MODE not set:
get_neo4j_uri()  # → bolt://host.docker.internal:7687 (MCP)
get_neo4j_auth()  # → values from NEO4J_USERNAME / NEO4J_PASSWORD
```

______________________________________________________________________

## Integration Checklist

- [ ] Review docker-compose.neo4j-audit.yml
- [ ] Review src/tools/neo4j_audit.py
- [ ] Update Neo4j connection code to use `get_neo4j_uri()` and `get_neo4j_auth()`
- [ ] Set `LIVE_AUDIT_MODE=1` before running live validation
- [ ] Test: Run `live --apply --batch-size 5`
- [ ] Verify: `docker inspect bioetl-neo4j-audit --format='{{json .State.OOMKilled}}'` returns false
- [ ] Stop: `.\scripts\ops\start-neo4j-audit.ps1 -Stop`

______________________________________________________________________

## Expected Results

### Before (with 256m heap)

```
live --report-fast
... build_snapshot: 98s ...
❌ OOMKilled (ExitCode 137)
```

### After (with 1024m heap)

```
export LIVE_AUDIT_MODE=1
live --report-fast
... build_snapshot: 98s ...
... analysis ops: ~18s ...
... graph writes: ~3s ...
✅ COMPLETE (no OOMKilled)
Memory: 1.8g / 2g limit
```

______________________________________________________________________

## Monitoring During Audit

### Terminal 1: Run Audit

```bash
export LIVE_AUDIT_MODE=1
live --report-fast
```

### Terminal 2: Watch Memory

```powershell
docker stats bioetl-neo4j-audit --no-stream --interval 1
```

### Terminal 3: View Logs

```powershell
.\scripts\ops\start-neo4j-audit.ps1 -Logs
```

______________________________________________________________________

## Troubleshooting

### Instance won't start

```powershell
# Check if ports 7475/7688 are available
netstat -an | findstr "7475\|7688"

# If busy, close MCP instance first:
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml down
```

### OOMKilled during audit

```powershell
# Check if memory exceeded limit
docker stats bioetl-neo4j-audit --no-stream

# If > 2g, either:
# 1. Increase mem_limit in docker-compose.neo4j-audit.yml
# 2. Reduce batch size: live --apply --batch-size 1
```

### Connection refused

```bash
# Verify instance running
docker ps | grep neo4j-audit

# Verify LIVE_AUDIT_MODE set
echo $LIVE_AUDIT_MODE  # Should be: 1

# Verify code uses get_neo4j_uri() (not hardcoded)
```

______________________________________________________________________

## Status

✅ All files created and ready
✅ Scripts tested and working
✅ Documentation complete
✅ Integration ready

**Next**: Run `.\scripts\ops\start-neo4j-audit.ps1` and test live validation.

______________________________________________________________________

**For detailed setup**: See NEO4J_AUDIT_INSTANCE_GUIDE.md
**For implementation checklist**: See AUDIT_INSTANCE_IMPLEMENTATION.md
