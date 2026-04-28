# Neo4j Backend Recovery - Quick Start

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

**Next**: Restart Docker Desktop, then run `.\scripts\neo4j-recovery-checklist.ps1`

Expect: 10 minutes total
