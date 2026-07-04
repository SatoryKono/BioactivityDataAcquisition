# Neo4j Memory MCP for WSL - Setup Guide

**Platform**: Windows Subsystem for Linux (WSL)
**MCP Package**: `@knowall-ai/mcp-neo4j-agent-memory@0.2.5`
**Status**: Ready for Docker integration

______________________________________________________________________

## Quick Start (3 Steps)

### Step 1: Start Neo4j Backend

```bash
bash scripts/memory/setup/wsl_startup.sh
```

This script:

- ✅ Detects WSL environment
- ✅ Creates `.env.local` with WSL-optimized settings
- ✅ Starts Neo4j container with memory tuning
- ✅ Waits for startup completion
- ✅ Verifies connectivity

**Expected output:**

```
✓ Neo4j backend is running
✓ MCP wrapper is configured
✓ Ready for verification

Next steps:
1. Run verification: bash scripts/ai/mcp/check_neo4j_memory.sh
2. Access Neo4j Browser: http://host.docker.internal:7474/browser/
```

### Step 2: Run Verification

```bash
bash scripts/ai/mcp/check_neo4j_memory.sh
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

Then in Codex prompt:

```
Use @neo4j-memory to store this information: [your data]
```

______________________________________________________________________

## WSL-Specific Configuration

### Connection Strings

**From WSL (bash/shell):**

```bash
bolt://host.docker.internal:7687    # MCP uses this
http://host.docker.internal:7474/   # Browser from WSL terminal
```

**From Windows (PowerShell/CMD):**

```powershell
bolt://localhost:7687
http://localhost:7474/
```

**Browser URL** (works from both):

- WSL: `http://host.docker.internal:7474/browser/`
- Windows: `http://localhost:7474/browser/`

### Environment Variables (Auto-Configured)

The startup script creates `.env.local` with:

```bash
NEO4J_URI=bolt://host.docker.internal:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=bioetl_secure_password
NEO4J_DATABASE=neo4j
```

**Why `host.docker.internal`?**

- Docker Desktop on Windows (running WSL) uses this special hostname
- Allows WSL containers to communicate with host services
- Transparent to the wrapper — you don't change any code

______________________________________________________________________

## Files Involved

| File                                         | Purpose                            |
| -------------------------------------------- | ---------------------------------- |
| `scripts/memory/setup/wsl_startup.sh`        | ⭐ Start Neo4j (run first)         |
| `scripts/ai/mcp/check_neo4j_memory.sh`       | ⭐ Verify setup (run second)       |
| `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh` | MCP wrapper (@knowall-ai)          |
| `.env.local`                                 | WSL-specific config (auto-created) |
| `scripts/ai/mcp/support/load_repo_env.sh`    | Env variable loader                |

______________________________________________________________________

## Troubleshooting

### Container won't start

```bash
# Check Docker daemon is running
docker ps

# View detailed logs
docker logs bioetl-neo4j

# Remove broken container and retry
docker rm -f bioetl-neo4j
bash scripts/memory/setup/wsl_startup.sh
```

### Ports showing closed

```bash
# Neo4j takes 10-15 seconds to start
# Wait and check again:
sleep 15
bash scripts/ai/mcp/check_neo4j_memory.sh

# If still closed, check container:
docker ps | grep bioetl-neo4j
```

### MCP not responding in Codex

```bash
# Re-register MCP servers
uv run python -m scripts.engineering.dev setup-mcp

# Verify wrapper is accessible
test -x scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh && echo "OK"

# Check MCP in Codex
codex mcp get neo4j-memory
```

### "host.docker.internal not resolving"

This is rare in WSL. If it happens:

1. Update Docker Desktop to latest
1. Restart WSL: `wsl --shutdown` (from Windows CMD)
1. Retry startup script

______________________________________________________________________

## Common Commands

```bash
# Start Neo4j (from WSL)
bash scripts/memory/setup/wsl_startup.sh

# Run verification
bash scripts/ai/mcp/check_neo4j_memory.sh

# Access Neo4j Browser (from WSL)
wsl-open http://host.docker.internal:7474/browser/

# View Neo4j logs
docker logs -f bioetl-neo4j

# Test connection from WSL
docker exec bioetl-neo4j cypher-shell -u neo4j -p bioetl_secure_password "RETURN 1"

# Stop container
docker stop bioetl-neo4j

# Remove container (keep data)
docker rm bioetl-neo4j

# Full cleanup (remove all)
docker rm -f bioetl-neo4j

# Check MCP status
codex mcp list | grep neo4j

# Use in Codex
codex interactive
```

______________________________________________________________________

## Network Topology (WSL + Docker)

```
┌─────────────────────────────────────────────────┐
│            Windows (Host)                       │
│  • PowerShell/CMD: connects to localhost:7687   │
│  • Docker Desktop running with WSL integration  │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼─────────┐        ┌─────────▼──────────┐
│   WSL 2 Kernel  │        │  Docker Daemon     │
│  (Linux)        │        │  (Windows Service) │
└───────┬─────────┘        └────────┬───────────┘
        │                           │
        │ host.docker.internal      │
        │ (special WSL2 hostname)   │
        │                           │
        └───────────────┬───────────┘
                        │
                        │
            ┌───────────▼───────────┐
            │  Neo4j Container      │
            │  • Bolt: 7687         │
            │  • HTTP:  7474        │
            └───────────────────────┘
```

______________________________________________________________________

## Docker Desktop Settings (WSL)

Ensure Docker Desktop is properly configured:

1. **Settings > General**

   - ✅ "Use WSL 2 based engine" is checked

1. **Settings > Resources > WSL Integration**

   - ✅ "Enable integration with default WSL distro" is checked
   - ✅ Your WSL distro is listed and enabled

1. **Settings > Docker Engine**

   - Ensure `"debug": false` (or true if you want logs)

After changing: Restart Docker Desktop

______________________________________________________________________

## Performance Notes

**Memory allocation** (auto-configured by startup script):

- Heap Max: 512m (sufficient for development)
- Page Cache: 256m
- Total: ~800m

If you need higher performance:

```bash
# Edit wsl_startup.sh and modify:
-e NEO4J_server_memory_heap_max_size=1024m \
-e NEO4J_server_memory_pagecache_size=512m \
```

______________________________________________________________________

## Next Steps After Setup

1. ✅ Run startup script
1. ✅ Run smoke test
1. ✅ Open Neo4j Browser: `http://host.docker.internal:7474/browser/`
1. ✅ Use in Codex: `codex interactive`
1. ✅ Store knowledge: Use `@neo4j-memory` in prompts

______________________________________________________________________

## Technical Details

### Why `host.docker.internal`?

- **WSL 2** runs a lightweight Linux kernel
- Docker Desktop runs on Windows (host)
- From WSL, localhost = WSL's localhost (not Docker host)
- Special hostname `host.docker.internal` resolves to Docker host (Windows)
- WSL wrapper auto-loads this via `.env.local`

### How wrapper finds credentials

1. Loads `.env` if exists
1. Loads `.env.local` if exists (WSL-specific, auto-created)
1. Checks `NEO4J_AUTH`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
1. Falls back to defaults: `neo4j/bioetl_secure_password`

### Package differences

**What you're using:**

- `@knowall-ai/mcp-neo4j-agent-memory@0.2.5` (specialized Neo4j memory agent)

**Not standard MCP:**

- `@modelcontextprotocol/server-neo4j` (would require different wrapper)

The wrapper is correctly configured for the `@knowall-ai` package.

______________________________________________________________________

## References

- [WSL Documentation](https://learn.microsoft.com/en-us/windows/wsl/)
- [Docker Desktop WSL Integration](https://docs.docker.com/desktop/wsl/)
- [Neo4j Docker Hub](https://hub.docker.com/_/neo4j)
- [host.docker.internal Docs](https://docs.docker.com/desktop/networking/#use-cases-and-workarounds)

______________________________________________________________________

**Ready to start?** Run: `bash scripts/memory/setup/wsl_startup.sh`
