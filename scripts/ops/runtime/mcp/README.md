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
| 8817–8818 | Docker gateway, pinned `mcp-mermaid@0.4.1` |
| 8820–8821 | github, fetch |
| 8822–8823 | prometheus, grafana |
| 8824–8825 | neo4j-cypher, neo4j-memory (optional) |
| 8826–8827 | memory, filesystem |
| 8828–8831 | code-analyzer, mcp-code-interpreter, mutmut, github-actions |

## Canonical daily recovery

The daily local contract is `stable/shared`: ten selected client entries,
nine required localhost endpoints, and remote/auth-managed `ref`. Tracked
portable manifests and the tracked Devin projection remain the full 21-server
inventory.

```bash
# 1) Materialize and persist the daily local projection. This does not edit .env.
python3 scripts/ai/codex/setup_mcp.py \
  --profile stable --transport-mode shared \
  --persist-local-profile --skip-codex-validation

# 2) Reconcile singleton endpoints under the governed startup timeout.
bash scripts/ai/codex/run-codex.sh mcp-setup

# 3) Restart clients that cache MCP config, then run static and bounded checks.
bash scripts/ai/codex/run-codex.sh mcp-static
python3 scripts/ai/codex/setup_mcp.py --check
python3 scripts/ai/codex/setup_mcp.py --check-local
bash scripts/ai/codex/run-codex.sh mcp-check \
  --profile stable --timeout 1 --overall-timeout 10 --no-write
codex mcp list

# Stop the host-process plane when explicitly needed.
bash scripts/ops/runtime/mcp/stop-shared.sh
```

`setup_mcp.py` persists an operator choice only with
`--persist-local-profile`. After generation, restart Codex, Cursor, VS Code,
Qodo, Gemini, or Grok if that client was already running. Static checks are
read-only and do not start services. Live readiness does not start Docker
Compose or optional monitoring stacks.

For Windows-native optional/heavy profiles, use `start-shared.ps1` and
`health-shared.ps1`; `apply-shared-to-grok.ps1` remains the explicit Grok
projection path. Run `scripts/ops/runtime/mcp/watchdog-shared.ps1 -Daily` for
the Windows watchdog and `scripts/ops/runtime/mcp/stop-shared.ps1` to stop that
host-process plane. Those commands do not change the daily `stable/shared`
selection unless an operator explicitly persists another profile.

`start-shared.sh --all` is the full acceptance path. A repeated invocation must
reuse the same managed PID for every endpoint.

On non-mirrored WSL networking, `docker` is owned by one native Windows Docker
MCP streaming gateway. `mermaid` is owned by one pinned Windows
`mcp-mermaid@0.4.1` Streamable HTTP process. Each is exposed to WSL clients
through one binary loopback relay; client URLs remain `127.0.0.1`.

Subset start:

```powershell
.\scripts\ops\runtime\mcp\start-shared.ps1 -Servers adr-analysis,deja,context7
```

Fallback (stdio only):

```bash
python3 scripts/ai/codex/setup_mcp.py \
  --profile stable --transport-mode stdio \
  --persist-local-profile --skip-codex-validation
```

## Safety

- Clients should only connect to `http://127.0.0.1:<port>/mcp`.
- Orphan cleanup never removes containers named `bioetl-*` or labeled
  `bioetl.mcp.shared=true`.
- Does not start BioETL main/neo4j/monitoring stacks.
- Do not reintroduce long-lived stdio MCP Compose (#6293).
- Compose `container_name` is optional Mode B only — not the default multi-client path.
