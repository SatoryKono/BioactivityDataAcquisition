# Neo4j Memory MCP - WSL Configuration Complete

**Date**: 2026-04-08  
**Platform**: Windows + WSL  
**MCP Package**: @knowall-ai/mcp-neo4j-agent-memory@0.2.5  
**Status**: ✅ Ready for startup

---

## What Was Done

✅ **WSL-Optimized Startup Script**
- `scripts/ops/wsl_neo4j_startup.sh` — Detects WSL, auto-configures `host.docker.internal`

✅ **Correct Smoke Test** 
- `scripts/ops/smoke_test_neo4j_mcp_knowall.sh` — Tests @knowall-ai package, not generic MCP

✅ **WSL Documentation**
- `docs/05-operations/deployment/WSL-NEO4J-SETUP.md` — Complete WSL setup guide

✅ **Environment Configuration**
- `.env.local` auto-created with `NEO4J_URI=bolt://host.docker.internal:7687`

---

## What You Do Next (On Your WSL Machine)

### Step 1: Run Startup Script
```bash
bash scripts/ops/wsl_neo4j_startup.sh
```

**This script will:**
1. Detect you're on WSL
2. Create `.env.local` with correct `host.docker.internal` URI
3. Start Neo4j container
4. Wait 10-15 seconds for startup
5. Show you connection details

**Expected output includes:**
```
From WSL (bash):
  Bolt URI: bolt://host.docker.internal:7687
  Browser:  http://host.docker.internal:7474/browser/

From Windows (PowerShell/CMD):
  Bolt URI: bolt://localhost:7687
  Browser:  http://localhost:7474/browser
```

### Step 2: Verify with Smoke Test
```bash
bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh
```

**Expected output:**
```
╔═══════════════════════════════════════════╗
║  ✓ ALL CRITICAL TESTS PASSED            ║
║  Neo4j Memory MCP (@knowall-ai) READY   ║
╚═══════════════════════════════════════════╝
```

### Step 3: Use in Codex
```bash
codex interactive
```

Then use `@neo4j-memory` in your prompts.

---

## Files You Need

| File | Location | Purpose |
|------|----------|---------|
| **wsl_neo4j_startup.sh** | `scripts/ops/` | ⭐ Run first |
| **smoke_test_neo4j_mcp_knowall.sh** | `scripts/ops/` | ⭐ Run second |
| **WSL-NEO4J-SETUP.md** | `docs/05-operations/deployment/` | Reference |
| **mcp_neo4j_memory_wrapper.sh** | `scripts/ops/` | (auto-used) |

---

## Why WSL-Specific Setup?

**The issue:** WSL can't access `localhost:7687` directly when Neo4j runs in Docker Desktop

**The solution:** Use `host.docker.internal` (special hostname that Docker Desktop provides)

**What we did:**
- Startup script detects WSL
- Auto-creates `.env.local` with `NEO4J_URI=bolt://host.docker.internal:7687`
- Wrapper loads this env var
- MCP connects to Neo4j transparently

**Result:** Zero code changes needed, everything just works™

---

## Command Reference

```bash
# Run startup (one-time)
bash scripts/ops/wsl_neo4j_startup.sh

# Verify everything
bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh

# Use Codex MCP
codex interactive

# Check status
docker ps | grep bioetl-neo4j

# View logs
docker logs -f bioetl-neo4j

# Stop
docker stop bioetl-neo4j

# Cleanup
docker rm -f bioetl-neo4j
```

---

## Architecture (WSL + Docker)

```
WSL Terminal (bash)
    ↓
neo4j-memory MCP (registered in Codex)
    ↓
mcp_neo4j_memory_wrapper.sh
    ├─ Loads: .env.local
    └─ Sets: NEO4J_URI=bolt://host.docker.internal:7687
    ↓
@knowall-ai/mcp-neo4j-agent-memory@0.2.5
    ↓
Neo4j 5.15 (Docker Container)
    └─ Accessible via: host.docker.internal:7687
       (from WSL) or localhost:7687 (from Windows)
```

---

## Browser Access (From WSL)

```bash
# Option 1: Copy-paste into Windows browser
# http://host.docker.internal:7474/browser/

# Option 2: From WSL terminal (if wsl-open installed)
# wsl-open http://host.docker.internal:7474/browser/

# Option 3: From Windows PowerShell
# start http://localhost:7474/browser/

# Credentials for all:
Username: neo4j
Password: bioetl_secure_password
```

---

## Troubleshooting (WSL-Specific)

### "Cannot connect to host.docker.internal"

This is rare. If it happens:
1. Update Docker Desktop to latest version
2. In Docker Desktop > Settings > Resources > WSL Integration, verify your distro is enabled
3. Restart Docker Desktop
4. From Windows CMD: `wsl --shutdown` (closes all WSL instances)
5. Retry: `bash scripts/ops/wsl_neo4j_startup.sh`

### Container starts but ports seem closed

WSL uses different localhost. This is expected:
- WSL localhost ≠ Windows localhost
- Use `host.docker.internal` from WSL
- Use `localhost` from Windows
- Both are correct, context-dependent

Smoke test will show the difference.

### MCP wrapper can't find credentials

If `.env.local` wasn't created:
```bash
# Manually create it:
cat > .env.local << EOF
NEO4J_URI=bolt://host.docker.internal:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=bioetl_secure_password
NEO4J_DATABASE=neo4j
EOF
```

Then re-run startup script.

---

## Verification Checklist

After running startup script:

- [ ] Startup script completed without errors
- [ ] `.env.local` was created
- [ ] Container is running: `docker ps | grep bioetl-neo4j`
- [ ] Smoke test passes: `bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh`
- [ ] MCP registered: `codex mcp get neo4j-memory`
- [ ] Browser accessible: `http://host.docker.internal:7474/browser/`

---

## What's Different from Linux/macOS

| Aspect | Linux/macOS | WSL |
|--------|-------------|-----|
| **Connection** | `bolt://localhost:7687` | `bolt://host.docker.internal:7687` |
| **Browser** | `http://localhost:7474` | `http://host.docker.internal:7474` |
| **Docker Access** | Docker daemon on host | Docker Desktop on Windows |
| **Setup Script** | `scripts/ops/neo4j_quick_start.sh` | `scripts/ops/wsl_neo4j_startup.sh` |

Everything else (MCP, wrapper, smoke test) is identical.

---

## Next: Copy-Paste Commands

Run these in order:

```bash
# 1. Start Neo4j
bash scripts/ops/wsl_neo4j_startup.sh

# 2. Wait for script to complete (10-15 seconds)

# 3. Verify everything works
bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh

# 4. Use in Codex
codex interactive
# Then: @neo4j-memory [your prompt]
```

---

## Support

If you hit issues:
1. Check `docs/05-operations/deployment/WSL-NEO4J-SETUP.md` (detailed guide)
2. Run smoke test again: `bash scripts/ops/smoke_test_neo4j_mcp_knowall.sh`
3. View logs: `docker logs bioetl-neo4j`
4. Check MCP: `codex mcp get neo4j-memory`

---

**Status**: ✅ Ready to run  
**Next Action**: `bash scripts/ops/wsl_neo4j_startup.sh`  
**Time to Completion**: ~5 minutes (including Neo4j startup)
