# Codex + WSL2 Setup - Quick Start

Codex MCP servers configured and running under WSL2 Docker Desktop.

## Current Status ✓

```
NAMES                   STATUS
bioetl-mcp-filesystem   Up (running)
bioetl-mcp-fetch        Up (running)
bioetl-mcp-github       Up (running)
bioetl-mcp-memory       Up (running)
bioetl-codex-config     Up (running)
```

## What This Does

These Docker containers run Model Context Protocol (MCP) servers that integrate with Anthropic's Codex assistant:

- **mcp-memory**: Persistent knowledge graph for context
- **mcp-filesystem**: Project file access
- **mcp-github**: GitHub integration (requires GITHUB_PERSONAL_ACCESS_TOKEN)
- **mcp-fetch**: HTTP/web fetching
- **mcp-codex-config**: Configuration service (port 9100)

## How to Use

### 1. Start the MCP Servers (Already Running)

```powershell
# PowerShell
.\scripts\codex-start-wsl.ps1

# Or bash (in WSL)
bash scripts/codex-start-wsl.sh
```

### 2. Configure Codex

In Anthropic Codex settings, add MCP servers that connect to:
- `memory`: stdio (local)
- `filesystem`: stdio (local)
- `github`: stdio (requires token in .env)
- `fetch`: stdio (local)

The servers are accessible on the warp-network bridge.

### 3. Verify Connection

```powershell
# Check server health
docker compose -f docker-compose.codex.yml ps

# View logs
docker compose -f docker-compose.codex.yml logs -f bioetl-mcp-memory
```

## Configuration Files

- **docker-compose.codex.yml**: MCP server definitions
- **.codex/settings.json**: Original Codex MCP config (reference)
- **.codex/config.toml**: Codex behavior settings
- **.env**: Environment variables (create from .env.example)

## Environment Variables

Add to `.env`:
```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxx
```

## Docker Commands

```bash
# Stop all MCP servers
docker compose -f docker-compose.codex.yml down

# Restart
docker compose -f docker-compose.codex.yml restart

# Logs
docker compose -f docker-compose.codex.yml logs -f

# Individual server logs
docker logs -f bioetl-mcp-memory
docker logs -f bioetl-mcp-filesystem
docker logs -f bioetl-mcp-github
docker logs -f bioetl-mcp-fetch
```

## Networking

- Network: `warp-network` (bridge, shared with monitoring stack)
- All services communicate via container names
- Host access: `localhost:9100` for Codex config

## WSL2 Performance Tips

Edit `C:\Users\{user}\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
```

Restart WSL:
```powershell
wsl --shutdown
```

## Troubleshooting

### MCP Servers not connecting
```powershell
docker compose -f docker-compose.codex.yml logs
docker network inspect warp-network
```

### GitHub auth fails
```powershell
# Check token in .env
type .env | Select-String GITHUB
```

### Memory or filesystem server errors
```powershell
docker logs bioetl-mcp-memory
docker logs bioetl-mcp-filesystem
```

## Next Steps

1. ✓ Docker containers running
2. Open Anthropic Codex
3. Add MCP servers to settings.json (use stdio connections)
4. Test each server individually
5. Start using Codex with your project

---

**Files Created:**
- `docker-compose.codex.yml` - MCP server stack
- `scripts/codex-start-wsl.sh` - Bash startup script
- `scripts/codex-start-wsl.ps1` - PowerShell startup script
- `docs/CODEX_WSL_SETUP.md` - Detailed setup guide
