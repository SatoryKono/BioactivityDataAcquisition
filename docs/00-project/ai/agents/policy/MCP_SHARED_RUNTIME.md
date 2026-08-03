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
| memory | T2 | wrapper stdio | shared port 8826; single-process file owner |
| filesystem | T2 | wrapper stdio | shared port 8827; repository-root allowlist |
| fetch | T2 | uvx wrapper | **Phase 2** port 8821 |
| github | T2 | wrapper | **Phase 2** port 8820 |
| docker | T2 | docker mcp gateway stdio | **catalog optional** port 8817 (`daily=false`) |
| context7 | T2 | wrapper | **daily** port 8815 |
| ast-grep | T2 | wrapper | **daily** port 8816 |
| mcp-code-interpreter | T2 | uvx stdio | shared port 8829 |
| prometheus | T2 | docker/wrapper | **daily** port 8822 |
| grafana | T2 | docker/wrapper | **daily** port 8823 |
| brave-search | T2 | docker run stdio | **daily** port 8811 |
| neo4j-cypher | T2 | wrapper | **catalog** port 8824 (needs healthy neo4j auth) |
| neo4j-memory | T2 | wrapper | **catalog** port 8825 (needs healthy neo4j auth) |
| mermaid | T2 | gateway stdio | **catalog optional** port 8818 (`daily=false`) |
| dockerhub | T2 | gateway stdio | **catalog optional** port 8819 (`daily=false`) |
| deja | T2 | npx stdio | **Phase 1** port 8814 |
| adr-analysis | T2 | npx stdio | **Phase 1 MVP** port 8813 |
| mutmut | T2 | wrapper | shared port 8830 |
| code-analyzer | T2 | wrapper | shared port 8828 |
| github-actions | T2 | wrapper | shared port 8831 |
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

## Shared endpoints (v4)

Catalog: `scripts/ops/runtime/mcp/shared-servers.json`  
Bridge pin: **`mcp-proxy@6.5.4`** (stdio → Streamable HTTP `/mcp`).

| Server group | Ports | Daily profile `shared` |
| --- | --- | --- |
| search/analysis | `8811`, `8813`–`8816` | yes |
| Docker gateway (`docker`, `mermaid`) | `8817`–`8818` | yes |
| GitHub/fetch/monitoring | `8820`–`8823` | yes |
| Neo4j | `8824`–`8825` | optional; included by `--all` |
| stateful memory/filesystem | `8826`–`8827` | yes |
| analyzer/interpreter/mutmut/actions | `8828`–`8831` | yes |

Exact names, ports, launch modes and readiness timeouts are owned by
`shared-servers.json`; `setup_mcp.py` loads that catalog rather than maintaining
a second endpoint map.

## Stateful servers

| Server | Accepted shared-state contract |
| --- | --- |
| `filesystem` | One repository-root allowlist shared by every local client; generated client config cannot expand it |
| `memory` | One server process owns a local worktree/branch/commit-scoped JSON under ignored `.cache/mcp-memory/`, serializing writes inside that process. The tracked JSON is a read-only seed, never the mutable runtime store. |

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
| Profile `shared` | Every sanctioned local MCP through the shared plane + remote HTTP MCP |

## Compose Mode B (optional — not default)

`container_name: bioetl-mcp-<name>` + published `127.0.0.1:88xx` can guard **one** compose project against a second `compose up`. That does **not** stop Docker MCP Toolkit random `docker run` thrash and must **not** reintroduce long-lived **stdio** Compose (#6293). Prefer host `mcp-proxy` plane (this document). Mode B only for Docker-native HTTP images with protocol healthchecks.

Localhost allowlist (not SaaS remote list):

`APPROVED_LOCAL_MCP_BASE_URL_PREFIXES = ("http://127.0.0.1:", "http://localhost:")`

## Security (v1)

| Rule | Detail |
| --- | --- |
| Client URLs | `127.0.0.1` / `localhost` only in generated config |
| Secrets | Env loaders + wrappers; never tracked JSON |
| Trust | Same OS user; not multi-tenant |
| Auth token | Optional: `BIOETL_MCP_SHARED_API_KEY` → mcp-proxy `--apiKey` / client `X-API-Key`; none mandatory in v1 |
| Bind | mcp-proxy `--host 127.0.0.1` (start-shared default) |
| Watchdog | `watchdog-shared.ps1 -Daily` restarts DOWN servers only |
| Mode B | Skeleton `docker-compose.mcp-shared.yml` — empty by default; no stdio Compose |
| #6293 | No TTY keepalive stdio Compose; readiness via `/ping` + protocol smoke |

## Ops lifecycle

```powershell
.\scripts\ops\runtime\mcp\start-shared.ps1
.\scripts\ops\runtime\mcp\health-shared.ps1
.\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1  # optional Grok projection; restart Grok afterward
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

## Singleton lifecycle

- Linux/WSL reconciliation holds one global `flock`.
- A live managed PID receives its full catalog readiness deadline; no competing
  retry is started.
- A ready listener without a managed PID fails as `unmanaged_ready`.
- Every mcp-proxy binds explicitly to `127.0.0.1`.
- On non-mirrored WSL networking, Docker MCP servers use one native Windows
  streaming gateway and a binary relay to WSL loopback.
- Runtime status and health JSON are replaced atomically.

## Related files

- `scripts/ops/runtime/mcp/**`
- `scripts/ai/codex/setup_mcp.py`
- `docs/DOCKER_QUICKSTART.md`
- `src/memory/curated/lessons/docker-desktop-wsl-stability-32gib.md`
