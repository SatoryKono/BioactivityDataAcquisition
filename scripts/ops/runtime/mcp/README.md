# Shared MCP plane (localhost Streamable HTTP)

One long-running process per logical MCP server so multiple AI clients can share
tools without N× stdio children. See:

- `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`
- GitHub #6563 program

## Inventory

Pinned bridge: `mcp-proxy@6.5.4` (stdio → Streamable HTTP `/mcp`).

Server ports and wrappers: `shared-servers.json`.

## Operator flow

```powershell
# 1) Start shared plane (host processes via mcp-proxy)
.\scripts\ops\runtime\mcp\start-shared.ps1

# 2) Materialize local IDE projections to HTTP URLs
$env:PYTHONPATH = (Resolve-Path .).Path
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation

# 3) Restart AI clients once

# 4) Health
.\scripts\ops\runtime\mcp\health-shared.ps1

# Stop
.\scripts\ops\runtime\mcp\stop-shared.ps1
```

Fallback (stdio only):

```powershell
python scripts/ai/codex/setup_mcp.py --profile stable --transport-mode stdio --skip-codex-validation
```

## Safety

- Clients should only connect to `http://127.0.0.1:<port>/mcp`.
- Orphan cleanup never removes containers named `bioetl-*` or labeled
  `bioetl.mcp.shared=true`.
- Does not start BioETL main/neo4j/monitoring stacks.
- Do not reintroduce long-lived stdio MCP Compose (#6293).
