# Shared MCP plane — operator playbook

Program: GitHub #6563. Policy: `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`.

## Daily multi-client (recommended on 32 GiB hosts)

```powershell
cd <repo>

# 1) Daily subset = catalog minus neo4j-* (auth optional)
.\scripts\ops\runtime\mcp\start-shared.ps1 -Daily
.\scripts\ops\runtime\mcp\health-shared.ps1
# Optional recovery loop:
# .\scripts\ops\runtime\mcp\watchdog-shared.ps1 -Daily

# 2) Point local IDE projections at localhost URLs
$env:PYTHONPATH = (Resolve-Path .).Path
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation
# Updates BOTH ~/.grok/config.toml and repo .grok/config.toml (project often still has stdio)
.\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1 -DisableDockerGateways

# 3) Full restart of AI clients (required — hot reload often keeps old stdio)
#    Grok: /mcps then r, or restart all windows. Project .grok/config.toml was a common
#    dual-spawn source (stdio) while user config already had shared HTTP.
#    Grok, Cursor, Codex, Gemini, VS Code

# 4) Optional one-shot (plane + projections + orphan cleanup)
# .\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1 `
#   -Profile shared -TransportMode shared -WithSharedMcp -SkipEnsureStable -KillHostGateways
```

## Fallback (single heavy client, stdio)

```powershell
python scripts/ai/codex/setup_mcp.py --profile stable --transport-mode stdio --skip-codex-validation
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -KillHostGateways
```

## Thrash recovery

Symptoms: many random-name containers (`docker-mcp-name=jetbrains|node-code-sandbox`),
many `docker mcp gateway` host processes, free RAM collapse.

```powershell
# Prefer AI clients idle first — they respawn children after kill.
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -KillHostGateways
.\scripts\ops\runtime\docker\reset-mcp-host-sessions.ps1   # report
# Apply: reset-mcp-host-sessions.ps1 -Execute -KillHostGateways
```

**Never** kills `bioetl`, `bioetl-neo4j`, `bioetl-*`, or label `bioetl.mcp.shared=true`.

## Toolkit rules

- Do **not** enable Docker Desktop MCP Toolkit full catalog / `MCP_DOCKER --profile default`.
- Disable Toolkit servers: `jetbrains`, `node-code-sandbox`.
- `container_name` in Compose is **not** a substitute for shared HTTP (see policy Mode B).

## Partial plane / flaky servers

- Docker-backed entries (brave, docker, mermaid, prometheus, …) need longer settle;
  `start-shared.ps1` retries and uses ≥45s settle for those names.
- `neo4j-*` need healthy Neo4j credentials; leave down if auth fails.
- Run **one** `start-shared` at a time (parallel runs kill each other’s trees).

## Optional loopback auth (W5)

```powershell
# Server: require X-API-Key on mcp-proxy
$env:BIOETL_MCP_SHARED_API_KEY = '<secret>'   # do not commit; machine-local only
.\scripts\ops\runtime\mcp\start-shared.ps1 -Daily

# Clients must send header X-API-Key (generator support TBD; manual for now).
```

Default is **no** API key (same-user localhost trust). Never bind non-loopback.

## Mode B Compose (optional — not default)

Skeleton only: `docker-compose.mcp-shared.yml` (empty services; profile `mode-b`).
Do **not** use for stdio MCP. Prefer host `start-shared.ps1 -Daily`.

## Watchdog

```powershell
.\scripts\ops\runtime\mcp\watchdog-shared.ps1 -Daily
# logs/mcp-shared/watchdog.json
```

## Stop

```powershell
.\scripts\ops\runtime\mcp\stop-shared.ps1
```
