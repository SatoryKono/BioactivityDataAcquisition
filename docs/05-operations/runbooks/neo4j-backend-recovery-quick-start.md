# Neo4j Backend Recovery - Quick Start

## TL;DR

1. **Restart Docker Desktop** (manual, takes 3 min):
   - Right-click tray icon → Quit
   - Wait 10 seconds
   - Relaunch → Wait 60 seconds

2. **Run automated recovery**:
   ```powershell
   .\scripts\neo4j-recovery-checklist.ps1
   ```

3. **If all green**: Backend ready ✅
4. **If any red**: Check `docker logs bioetl-neo4j` for errors

---

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

---

## Recovery Script Workflow

The `neo4j-recovery-checklist.ps1` does:

1. ✅ Verify Docker daemon responsive
2. ✅ Clean old container
3. ✅ Start Neo4j 5.13-community
4. ⏳ Wait 60 seconds (startup)
5. ✅ Check container status
6. ✅ Test HTTP port (7474)
7. ✅ Test Bolt driver (7687)
8. ✅ Verify environment config

**Expected output**: Green checkmarks, final line says "BACKEND READY"

---

## If Tests Fail

Check the specific error message, then:

| Error | Cause | Fix |
|-------|-------|-----|
| "docker ps hangs" | Docker daemon frozen | Restart again |
| "Container Exited" | Startup failed | `docker logs bioetl-neo4j \| tail` |
| "HTTP timeout" | Startup incomplete | Wait 30 more seconds |
| "ECONNRESET on Bolt" | Protocol/config issue | Check logs for OOM/errors |

---

## After Backend Works

```bash
# In Codex (any shell)
codex interactive

# Use the memory MCP
# Type: "Use @neo4j-memory to remember this"
# Should work if backend responded to test
```

---

## Files Reference

| Need | File |
|------|------|
| Automated recovery | `scripts/neo4j-recovery-checklist.ps1` |
| Manual Docker restart | `scripts/restart-docker.ps1` |
| WSL setup | `scripts/setup-neo4j-wsl.sh` |
| Docker Compose | `docker-compose.neo4j.yml` |
| Bolt test | `test_neo4j_connection.js` (repo root) |
| Detailed guide | `NEO4J_COMPLETE_RECOVERY_GUIDE.md` |
| What changed | `CRITICAL_ISSUES_FIXED.md` |

---

## Root Cause (Honest Assessment)

We don't know yet. Possibilities:
1. **Startup instability** ← Most likely (symptoms match)
2. **Memory exhaustion** ← Fixed by reducing heap
3. **TLS encryption** ← Fixed by adding `encryption: 'ENCRYPTION_OFF'`
4. **Docker daemon issue** ← Fixed by manual restart

Once tests run, we'll see which one was actually broken.

---

**Next**: Restart Docker Desktop, then run `.\scripts\neo4j-recovery-checklist.ps1`

Expect: 10 minutes total
