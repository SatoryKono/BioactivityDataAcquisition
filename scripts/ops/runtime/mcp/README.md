# Shared MCP plane (localhost Streamable HTTP)

One long-running process per logical MCP server so multiple AI clients can share
tools without N× stdio children. See:

- `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`
- `OPERATOR.md` (daily + thrash recovery)
- GitHub #6563 program

## Inventory

Pinned bridge: `mcp-proxy@6.5.4` (stdio → Streamable HTTP `/mcp`).

Server ports, wrappers, state models and launch modes:
`shared-servers.json` (v4 runtime SSOT).

| Port | Server |
| --- | --- |
| 8811 | brave-search |
| 8813–8816 | adr-analysis, deja, context7, ast-grep |
| 8817–8818 | docker, mermaid |
| 8820–8821 | github, fetch |
| 8822–8823 | prometheus, grafana |
| 8824–8825 | neo4j-cypher, neo4j-memory (optional) |
| 8826–8827 | memory, filesystem |
| 8828–8831 | code-analyzer, mcp-code-interpreter, mutmut, github-actions |

## Operator flow

```powershell
# 1) Start shared plane (host processes via mcp-proxy)
# Daily = all local servers except optional neo4j-*
.\scripts\ops\runtime\mcp\start-shared.ps1 -Daily
# Optional: .\scripts\ops\runtime\mcp\watchdog-shared.ps1 -Daily

# 2) Materialize local IDE projections to HTTP URLs
$env:PYTHONPATH = (Resolve-Path .).Path
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation
# Optional: rewrite tracked workspace MCP JSON files onto shared HTTP URLs
# (does not start the plane; do not commit the rewritten local files).
python scripts/ops/runtime/mcp/_materialize_shared_http_configs.py
# Rewrites BOTH ~/.grok/config.toml and repo .grok/config.toml when present
# (project stdio was a common dual-spawn source next to user HTTP).
.\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1 -DisableDockerGateways

# 3) Restart AI clients once (required; Grok: /mcps then r)

# 4) Health
.\scripts\ops\runtime\mcp\health-shared.ps1

# Stop
.\scripts\ops\runtime\mcp\stop-shared.ps1
```

`start-shared.sh --all` is the full acceptance path. A repeated invocation must
reuse the same managed PID for every endpoint.

On non-mirrored WSL networking, `docker` and `mermaid` are owned by one native
Windows streaming gateway each and exposed to WSL clients through a binary
loopback relay. Client URLs remain `127.0.0.1`.

Subset start:

```powershell
.\scripts\ops\runtime\mcp\start-shared.ps1 -Servers adr-analysis,deja,context7
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
- Compose `container_name` is optional Mode B only — not the default multi-client path.
