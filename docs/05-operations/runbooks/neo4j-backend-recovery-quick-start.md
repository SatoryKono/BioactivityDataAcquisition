______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only optional Neo4j memory backend for AI/runtime tooling.
  Last verified: '2026-05-13'

______________________________________________________________________

# Neo4j Backend Recovery - Quick Start

## Trigger

- Use this runbook when the optional Neo4j memory backend is unavailable,
  `docker ps` hangs, Bolt/HTTP health checks fail, or AI memory tooling reports
  Neo4j connectivity errors.
- Do not use it for BioETL pipeline runtime recovery; this backend is an
  auxiliary memory surface, not a required ETL dependency.

## Impact

- Priority: P2.
- Delayed recovery reduces AI memory retrieval quality and graph-backed
  diagnostics, but does not block local-only BioETL pipeline execution.

## Preconditions

- Docker Desktop is installed and available to the local operator.
- The repository checkout contains the Neo4j recovery scripts listed below.
- No production BioETL runtime must be stopped to recover this optional memory
  backend.

## TL;DR

1. **Restart Docker Desktop** (manual, takes 3 min):

   - Right-click tray icon → Quit
   - Wait 10 seconds
   - Relaunch → Wait 60 seconds

1. **Run automated recovery**:

   ```powershell
   .\scripts\neo4j-recovery-checklist.ps1
   ```

1. **If all green**: Backend ready ✅

1. **If any red**: Check `docker logs bioetl-neo4j` for errors

______________________________________________________________________

## What Changed

**Fixed**:

- ✅ WSL scripts now use `docker.exe` (Windows daemon)
- ✅ WSL scripts test `host.docker.internal` (not localhost)
- ✅ Test files loaded from repo root (not /tmp)
- ✅ Removed false claim: "TLS is root cause" → "TLS suspected but unconfirmed"
- ✅ Reduced memory: 512m → 256m heap (stability)

**Already correct**:

- ✅ MCP configuration 100% ready
- ✅ Environment variables synchronized
- ✅ Test scripts in right location

______________________________________________________________________

## Recovery Script Workflow

## Procedure

The `neo4j-recovery-checklist.ps1` does:

1. ✅ Verify Docker daemon responsive
1. ✅ Clean old container
1. ✅ Start Neo4j 5.13-community
1. ⏳ Wait 60 seconds (startup)
1. ✅ Check container status
1. ✅ Test HTTP port (7474)
1. ✅ Test Bolt driver (7687)
1. ✅ Verify environment config

**Expected output**: Green checkmarks, final line says "BACKEND READY"

______________________________________________________________________

## If Tests Fail

Check the specific error message, then:

| Error                | Cause                 | Fix                                |
| -------------------- | --------------------- | ---------------------------------- |
| "docker ps hangs"    | Docker daemon frozen  | Restart again                      |
| "Container Exited"   | Startup failed        | `docker logs bioetl-neo4j \| tail` |
| "HTTP timeout"       | Startup incomplete    | Wait 30 more seconds               |
| "ECONNRESET on Bolt" | Protocol/config issue | Check logs for OOM/errors          |

______________________________________________________________________

## After Backend Works

```bash
# In Codex (any shell)
codex interactive

# Use the memory MCP
# Type: "Use @neo4j-memory to remember this"
# Should work if backend responded to test
```

______________________________________________________________________

## Files Reference

| Need                  | File                                   |
| --------------------- | -------------------------------------- |
| Automated recovery    | `scripts/ops/runtime/neo4j/neo4j-recovery-checklist.ps1` |
| Manual Docker restart | `scripts/ops/runtime/docker/restart-docker.ps1` |
| WSL setup             | `scripts/memory/setup/wsl_startup.sh` |
| Docker Compose        | `docker-compose.neo4j.yml`             |
| MCP/backend check     | `scripts/ai/mcp/check_neo4j_memory.sh` |
| Detailed guide        | `docs/05-operations/runbooks/neo4j-complete-recovery-guide.md` |
| Memory sync/query     | `scripts/memory/README.md` |

______________________________________________________________________

## Root Cause (Honest Assessment)

We don't know yet. Possibilities:

1. **Startup instability** ← Most likely (symptoms match)
1. **Memory exhaustion** ← Fixed by reducing heap
1. **TLS encryption** ← Fixed by adding `encryption: 'ENCRYPTION_OFF'`
1. **Docker daemon issue** ← Fixed by manual restart

Once tests run, we'll see which one was actually broken.

______________________________________________________________________

## Verification

- `scripts/ops/runtime/neo4j/neo4j-recovery-checklist.ps1` reports backend
  ready.
- HTTP port `7474` and Bolt port `7687` checks pass.
- `scripts/ai/mcp/check_neo4j_memory.sh` or the local MCP backend check can
  connect without authentication/configuration errors.

## Rollback/Recovery

- If recovery makes the local Docker state worse, stop and remove only the
  reviewed `bioetl-neo4j` container, then restart Docker Desktop.
- Restore previous MCP/backend configuration from git if configuration files
  were edited during diagnosis.
- Escalate to the detailed Neo4j recovery guide if the quick-start checklist
  still fails after one clean Docker restart.

## Post-incident

- Record the failing check, final recovery action, and any changed local
  configuration in the related issue or session note.
- Update this quick-start if the root cause becomes known and repeatable.

## Compliance

- Local-only posture remains unchanged; do not make Neo4j a required BioETL
  runtime service.
- Do not store secrets or provider credentials in Neo4j recovery logs.

**Next**: Restart Docker Desktop, then run `.\scripts\neo4j-recovery-checklist.ps1`

Expect: 10 minutes total
