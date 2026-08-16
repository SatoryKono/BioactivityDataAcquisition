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
| docker | T2 | Windows Docker MCP streaming gateway | **daily** port 8817 |
| context7 | T2 | wrapper | **daily** port 8815 |
| ast-grep | T2 | wrapper | **daily** port 8816 |
| mcp-code-interpreter | T2 | uvx stdio | shared port 8829 |
| prometheus | T2 | docker/wrapper | **daily** port 8822 |
| grafana | T2 | docker/wrapper | **daily** port 8823 |
| brave-search | T2 | docker run stdio | **daily** port 8811 |
| neo4j-cypher | T2 | wrapper | **catalog** port 8824 (needs healthy neo4j auth) |
| neo4j-memory | T2 | wrapper | **catalog** port 8825 (needs healthy neo4j auth) |
| mermaid | T2 | pinned `mcp-mermaid@0.4.1` Windows-native streaming | **daily** port 8818 |
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
| Devin | Yes (`type: http` + URL) | Tracked projection remains the full sanctioned inventory |

## Shared endpoints (v4)

Catalog: `scripts/ops/runtime/mcp/shared-servers.json`  
Bridge pin: **`mcp-proxy@6.5.4`** (stdio → Streamable HTTP `/mcp`).

| Server group | Ports | Daily profile `shared` |
| --- | --- | --- |
| search/analysis | `8811`, `8813`–`8816` | yes |
| Windows-native streaming (`docker` gateway, pinned `mermaid`) | `8817`–`8818` | yes |
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
python3 scripts/ai/codex/setup_mcp.py \
  --profile stable --transport-mode shared \
  --persist-local-profile --skip-codex-validation
```

| Surface | Behavior |
| --- | --- |
| Tracked `.mcp.json` / `scripts/ai/.mcp.json` / `.zed` | Always **full portable stdio** (+ remote HTTP T4) |
| Tracked `.devin/mcp_config.json` | Always full sanctioned shared-HTTP inventory with Devin header syntax |
| Local `.cursor` / `.vscode` / `.qodo` / workspace Codex / optional Gemini | Persisted profile + **transport-mode** |
| `--transport-mode stdio` | Explicit single-client fallback; wrappers only |
| `--transport-mode shared` | Default; shared-capable servers become `type: http` localhost URLs |
| `--transport-mode hybrid` | Same as shared for catalog servers; others stay stdio |
| Profile `shared` | Every sanctioned local MCP through the shared plane + remote HTTP MCP |

The daily selection is profile `stable` with transport `shared`: exactly ten
client entries, of which nine are required localhost endpoints and `ref` is
remote/auth-managed.

## Deterministic cold start and offline preflight

`scripts/ai/codex/helper/ensure-mcp.sh` is the sole owner of the shared-plane
start timeout. `CODEX_MCP_SHARED_START_TIMEOUT` defaults to 360 seconds and
bounds `start-shared.sh`; callers must not wrap ensure with a smaller
undocumented timeout. Configuration materialization has its separate bounded
`CODEX_MCP_SETUP_TIMEOUT` phase. Failures identify materialization, plane start,
or post-start health verification and point to `logs/mcp-shared/status.json`
and per-server `*.err.log` files.

Healthy endpoints are checked before launch. Repeated ensure calls reuse the
managed singleton listeners and do not create competing processes. Static
validation never starts services. Stable POSIX wrappers support
`BIOETL_MCP_VALIDATE_ONLY=1`; this mode checks local prerequisites and exits
before package execution or registry access.

```bash
BIOETL_MCP_VALIDATE_ONLY=1 \
  bash scripts/ai/mcp/mcp_ast_grep_wrapper.sh
bash scripts/ai/codex/run-codex.sh mcp-static
```

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
- On non-mirrored WSL networking, `docker` uses one native Windows Docker MCP
  gateway and `mermaid` uses one pinned Windows `mcp-mermaid@0.4.1` process;
  each has one binary relay to WSL loopback.
- Runtime status and health JSON are replaced atomically.

## Related files

- `scripts/ops/runtime/mcp/**`
- `scripts/ai/codex/setup_mcp.py`
- `docs/DOCKER_QUICKSTART.md`
- `src/memory/curated/lessons/docker-desktop-wsl-stability-32gib.md`
