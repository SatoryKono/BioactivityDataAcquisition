# MCP_SHARED_RUNTIME.md

*Status: internal-published (AI runtime shared MCP plane)*
*Program: GitHub #6563*

## Purpose

Define how BioETL runs a **localhost shared MCP plane** so multiple AI clients
can use the same logical server instance without N× stdio process/container
thrash on 32 GiB Windows hosts.

## Relationship to other policy

| Document | Role |
| --- | --- |
| `MCP_LOCAL_RUNTIME_CONFIG.md` | Portable vs local projections, profiles, tokens |
| This file | Shared Streamable HTTP plane design + operator contract |
| #6293 | Long-lived **stdio** MCP Compose is **retired** — do not reintroduce |

## Why stdio multiplies

Stdio MCP is **1 client ↔ 1 process**. Each Grok/Cursor reconnect can leave
orphans. Docker Desktop MCP Toolkit may also spawn **jetbrains** /
**node-code-sandbox** outside BioETL inventory (`docker-mcp=true` labels).

Already multi-client without local plane: remote HTTP `deepwiki`, `ref`.

## Transport choice

| Transport | Multi-client | BioETL stance |
| --- | --- | --- |
| **Streamable HTTP** (MCP 2025-03) | Yes | **Preferred** for shared plane |
| HTTP+SSE (legacy) | Yes | Avoid new work |
| stdio | No | Default portable + single-client fallback |
| Remote SaaS HTTP | Yes | `deepwiki`, `ref` only (allowlist) |

## Server transport matrix (21-server inventory)

Classes:

- **T1** — native HTTP / easy flag (future native)
- **T2** — stdio-only today → bridge via pinned `mcp-proxy`
- **T3** — Docker Desktop Toolkit only (out of BioETL SSOT)
- **T4** — remote HTTP already shared

| Server | Class | Launch today | Shared plane |
| --- | --- | --- | --- |
| deepwiki | T4 | remote HTTP | already shared |
| ref | T4 | remote HTTP | already shared |
| memory | T2 | npx stdio | later |
| filesystem | T2 | npx stdio | later (stateful roots) |
| fetch | T2 | uvx wrapper | later |
| github | T2 | wrapper | later |
| docker | T2 | docker mcp gateway stdio | later / ops |
| context7 | T2 | wrapper | **Phase 1** port 8815 |
| ast-grep | T2 | wrapper | **Phase 1** port 8816 |
| mcp-code-interpreter | T2 | uvx stdio | later |
| prometheus | T2 | docker/wrapper | later |
| grafana | T2 | docker/wrapper | later |
| brave-search | T2 | docker run stdio | **Phase 1** port 8811 |
| neo4j-cypher | T2 | wrapper | later |
| neo4j-memory | T2 | wrapper | later |
| mermaid | T2 | gateway stdio | later |
| deja | T2 | npx stdio | **Phase 1** port 8814 |
| adr-analysis | T2 | npx stdio | **Phase 1 MVP** port 8813 |
| mutmut | T2 | wrapper | later |
| code-analyzer | T2 | wrapper | later |
| github-actions | T2 | wrapper | later |
| jetbrains | T3 | Desktop Toolkit | disable in Desktop |
| node-code-sandbox | T3 | Desktop Toolkit | disable in Desktop |

## Client capability matrix (local HTTP URLs)

| Client | `type: http` + URL | Notes |
| --- | --- | --- |
| Cursor | Yes (mcp.json) | Primary target for local projections |
| VS Code / Copilot | Yes (servers map) | Same generator path |
| Codex | Yes (url in config.toml / settings) | Workspace + `~/.codex` |
| Grok | Yes when projection loaded | Restart client after materialize |
| Qodo | Yes (mcp.json) | Local profile |
| Devin | Yes (`type: http` + URL) | Active projection follows the selected local profile |

## Shared endpoints (v1)

Catalog: `scripts/ops/runtime/mcp/shared-servers.json`

Bridge pin: **`mcp-proxy@6.5.4`** (stdio → Streamable HTTP `/mcp`).

| Server | URL |
| --- | --- |
| adr-analysis | `http://127.0.0.1:8813/mcp` |
| deja | `http://127.0.0.1:8814/mcp` |
| context7 | `http://127.0.0.1:8815/mcp` |
| ast-grep | `http://127.0.0.1:8816/mcp` |
| brave-search | `http://127.0.0.1:8811/mcp` |

## Generator contract

```bash
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation
```

| Surface | Behavior |
| --- | --- |
| Tracked `.mcp.json` / `scripts/ai/.mcp.json` / `.zed` | Always **full portable stdio** (+ remote HTTP T4) |
| Active `.devin` + local `.cursor` / `.vscode` / `.qodo` / workspace codex / gemini | Profile + **transport-mode** |
| `--transport-mode stdio` | Explicit single-client fallback; wrappers only |
| `--transport-mode shared` | Default; shared-capable servers become `type: http` localhost URLs |
| `--transport-mode hybrid` | Same as shared for catalog servers; others stay stdio |
| Profile `shared` | Membership = `stable` + `brave-search` (multi-client daily) |

Localhost allowlist (not SaaS remote list):

`APPROVED_LOCAL_MCP_BASE_URL_PREFIXES = ("http://127.0.0.1:", "http://localhost:")`

## Security (v1)

| Rule | Detail |
| --- | --- |
| Client URLs | `127.0.0.1` / `localhost` only in generated config |
| Secrets | Env loaders + wrappers; never tracked JSON |
| Trust | Same OS user; not multi-tenant |
| Auth token | Optional later (mcp-proxy `--apiKey`); none mandatory in v1 |
| #6293 | No TTY keepalive stdio Compose; readiness via `/ping` + protocol smoke |

## Ops lifecycle

```powershell
.\scripts\ops\runtime\mcp\start-shared.ps1
.\scripts\ops\runtime\mcp\health-shared.ps1
.\scripts\ops\runtime\mcp\stop-shared.ps1
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1   # never kills bioetl-* / shared labels
.\scripts\ops\runtime\docker\reset-mcp-host-sessions.ps1  # report; -Execute for actions
```

## Operator thrash checklist (no shared plane)

1. One `grok.exe` (or one heavy client)
2. Restart client after `apply-docker-stable-mcp.ps1 -Profile stable`
3. Disable Desktop Toolkit jetbrains / node-code-sandbox
4. Idle: `cleanup-mcp-orphans.ps1 -KillHostGateways`
5. Avoid parallel full-MCP clients

## Open decisions (resolved for v1)

| Decision | Choice |
| --- | --- |
| First shared server | **adr-analysis** (+ deja/context7/ast-grep/brave in same plane) |
| Bridge | Host **mcp-proxy@6.5.4**, not long-lived stdio Compose |
| Auth on loopback | None in v1 |
| Grok | Same local projection as Cursor after restart |

## Related files

- `scripts/ops/runtime/mcp/**`
- `scripts/ai/codex/setup_mcp.py`
- `docs/DOCKER_QUICKSTART.md`
- `src/memory/curated/lessons/docker-desktop-wsl-stability-32gib.md`
