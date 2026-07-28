# Plan: Shared MCP for multiple AI clients (actualized 2026-07-24)

*Status: Working planning artifact (non-normative)*
*Created: 2026-07-24*
*Source session plan: Grok plan mode `shared MCP HTTP`*
*Related closed work: #6293 (retire long-lived stdio MCP Compose), #6505 (least-privilege profiles)*

## Why duplicates still exist (root cause)

Code (`setup_mcp --profile stable`, `cleanup-mcp-orphans`, wrappers) **cannot forbid already-running clients**. Duplicates are produced **outside** BioETL compose:

| Mechanism | Effect |
| --- | --- |
| Stdio MCP = 1 client ↔ 1 process | N Grok/Cursor sessions ⇒ up to N full server sets |
| Client reconnect / crash | Old children often survive; new set +1 |
| Docker Desktop MCP Toolkit (`--profile default`) | Spawns **jetbrains**, **node-code-sandbox** not in BioETL inventory |
| Live session keeps Docker MCP tools | After orphan kill, client **respawns** gateways/containers |
| Profile files change only on client restart | Running `grok.exe` ignores new `.cursor/mcp.json` until restart |

**Not** a `bioetl` / `bioetl-neo4j` compose bug.

### Live evidence (host, 2026-07-24 ~10:00 local)

| Surface | Count | Notes |
| --- | --- | --- |
| `grok.exe` | **6** | Primary multiplier (sessions since 2026-07-23 ~18:46) |
| host `deja` | ~25 | npx/stdio thrash |
| host `mcp-adr-analysis` | ~22 | npx/stdio thrash |
| host `docker mcp gateway` | ~22 | docker/mermaid/dockerhub/default |
| host `ast-grep` | ~10 | stdio |
| host `context7` | ~8 | stdio |
| Docker `jetbrains` (Toolkit) | 5 | labels `docker-mcp-name=jetbrains` — **not** in BioETL SSOT |
| Docker `node-code-sandbox` | 5 | Toolkit — **not** in BioETL SSOT |
| Docker `mcp/brave-search` | 3 | BioETL wrapper `bioetl.mcp=brave-search` |
| `bioetl` / `bioetl-neo4j` | 1 each | unrelated to MCP thrash |

Local projection check: `.cursor/mcp.json` = **11** servers (`stable`); tracked `.mcp.json` = **21** portable full. Session still pulls Docker MCP Toolkit + residual gateways → files alone do not drain live processes.

## Problem statement (product)

Almost every BioETL MCP server is **stdio** (`command` → wrapper → `npx` / `docker run -i` / `docker mcp gateway --transport stdio`). Only `deepwiki` and `ref` are remote HTTP and already multi-client.

Goal: **one long-running MCP endpoint per logical server (or multiplex gateway), many clients**, without abandoning portable tracked inventory, ADR-010 local-first defaults, or reintroducing #6293-style long-lived **stdio** Compose.

## Goals / non-goals

### Goals

1. Multiple AI clients can share the **same** local MCP service instance (Streamable HTTP preferred).
2. Cut thrash: no N× containers/gateways/host npx for migrated servers.
3. Fit profiles `stable` / `core` / `ops` / `graph` / `full` and `setup_mcp.py`.
4. Tracked `.mcp.json` remains portable **stdio** SSOT; local projections may opt into shared URLs.
5. Localhost-only; secrets via env/wrappers; explicit start/stop/health/cleanup.
6. Ops path that does **not** fight live clients forever (operator discipline + shared plane).

### Non-goals (v1)

- Replacing remote SaaS MCP (`deepwiki`, `ref`).
- Forcing all 21 servers onto HTTP in one PR.
- Multi-machine / team gateway.
- Changing BioETL application compose contracts.
- Reintroducing `docker-compose.codex.yml` long-lived **stdio** MCP (#6293 closed that door).

## Constraints

| Constraint | Implication |
| --- | --- |
| `MCP_LOCAL_RUNTIME_CONFIG.md` | Tracked full inventory; profiles filter **local** projections |
| `APPROVED_REMOTE_MCP_BASE_URLS` | Localhost shared URLs need a **separate** local allowlist (not SaaS list) |
| ADR-010 | Shared stack is local process/containers only |
| Tech-debt budgets | No increases |
| MCP 2025-03 | Prefer Streamable HTTP; avoid new classic SSE |
| #6293 | Shared plane ≠ unbounded restart stdio Compose; prove initialize/list-tools readiness |
| Windows + Docker Desktop | Prefer host process for npm/uvx; Docker only when needed; **one** named container |

## Current baseline (verified)

| Area | State |
| --- | --- |
| Profiles | **Done** — `stable`/`core`/`ops`/`graph`/`full` in `setup_mcp.py` (#6505) |
| Orphan cleanup | **Done** — `cleanup-mcp-orphans.ps1` (+ `-KillHostGateways`) |
| Apply stable | **Done** — `apply-docker-stable-mcp.ps1` |
| Host harden | **Done** — `ensure-stable.ps1`, `harden-desktop-host.ps1` |
| Shared HTTP plane | **Missing** — no `scripts/ops/runtime/mcp/`, no `MCP_SHARED_RUNTIME.md` |
| `--transport-mode` | **Missing** — generator only emits stdio wrappers + 2 remote HTTP |
| Toolkit off | **Ops-only** — jetbrains/sandbox not controllable from BioETL SSOT |

```text
Client A --stdio--> process A     } duplicates under multi-client
Client B --stdio--> process B
Client * --HTTP---> deepwiki/ref  } already shared
```

## Target architecture

```text
  Grok / Cursor / Codex / ...
       |  HTTP (streamable)
       v
  Shared MCP plane (127.0.0.1 only)
    one process/container per logical server
    (optional later: single reverse-proxy multiplex)
```

**Mode A (MVP):** per-server named services (`bioetl-mcp-<name>` on `127.0.0.1:88xx`).
**Mode B (later):** single multiplex gateway if port sprawl hurts.

### Priority actualization (ROI, 2026-07-24)

Original plan prioritized Docker `brave` / gateway. Live counts show **host npx stdio** multiplies harder than brave containers.

| Priority | Candidates | Rationale |
| --- | --- | --- |
| P0 ops (no code) | Close extra Grok; disable Desktop Toolkit jetbrains/sandbox | Immediate RAM relief |
| Phase 1 shared (host) | `adr-analysis`, `deja`, `context7`, `ast-grep` | Highest host process counts |
| Phase 1 shared (docker) | `brave-search` | Named shared container vs N× `docker run -i` |
| Phase 2 | `github`, gateway-backed docker/mermaid alternatives | After MVP smoke |
| Out of SSOT | jetbrains, node-code-sandbox | Desktop Toolkit only — document disable |

## Phased delivery

### Phase 0 — Discovery and matrix (no cutover)

**Deliverables**

1. Inventory: 21 servers → native transports (stdio / streamable-http / docker-only / remote).
2. Classes: T1 native HTTP, T2 stdio-only (bridge), T3 Toolkit-only, T4 remote shared.
3. Client matrix: Grok / Cursor / Codex / VS Code / Qodo — `type: http` for localhost.
4. Security: bind `127.0.0.1` only; same-user trust boundary.

**Artifacts**

- `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md` (new design SSOT)
- Pointer + rules in `MCP_LOCAL_RUNTIME_CONFIG.md`

**Exit**

- Priority list ≤4 Phase-1 servers (include ≥1 host + optional brave).
- Confirmed config shape for Cursor + one of Grok/Codex.

### Phase 1 — Shared plane MVP

#### 1.1 Runtime layout

```text
scripts/ops/runtime/mcp/
  docker-compose.mcp-shared.yml   # optional; only if Docker path used
  start-shared.ps1 / .sh
  stop-shared.ps1 / .sh
  health-shared.ps1 / .sh
  README.md
scripts/ai/mcp/support/mcp_shared_env.ps1|.sh
scripts/ai/mcp/bridges/           # only if stdio→HTTP needed
```

Rules if Docker used:

- `container_name: bioetl-mcp-<name>`
- `restart: unless-stopped` only with **health/protocol** readiness (not #6293 TTY keepalive)
- `mem_limit` modest; ports `127.0.0.1:88xx:...`
- labels `bioetl.mcp.shared=true`, `bioetl.mcp.name=...`
- project `-p bioetl-mcp-shared` — never collide with main/neo4j

Prefer **host process** for npm/uvx servers.

#### 1.2 Generator (`setup_mcp.py`)

- `--transport-mode stdio|shared|hybrid` (default **stdio**).
- New profile `shared` (or transport-mode on existing membership) emits:

```json
"adr-analysis": {
  "type": "http",
  "url": "http://127.0.0.1:8813/mcp",
  "startup_timeout_sec": 30
}
```

- `APPROVED_LOCAL_MCP_BASE_URL_PREFIXES = ("http://127.0.0.1:", "http://localhost:")`.
- Tracked portable `.mcp.json` stays **stdio** SSOT.
- Local projections (`.cursor`, `.vscode`, `.qodo`, workspace codex) get shared URLs when requested.

#### 1.3 Bridges

Only when server lacks native HTTP: pin stdio→streamable-http bridge; one process per server under `start-shared`.

#### 1.4 Ops integration

| Action | Behavior |
| --- | --- |
| `start-shared` / `stop-shared` / `health-shared` | lifecycle of shared plane only |
| `cleanup-mcp-orphans.ps1` | **never** remove `bioetl-mcp-*` / label `bioetl.mcp.shared=true` |
| `ensure-stable.ps1` | do not treat shared stack as foreign |
| `apply-docker-stable-mcp.ps1` | optional `-TransportMode shared` |

#### 1.5 Validation

- Unit: shared mode emits HTTP; portable full remains stdio.
- Smoke: extend `protocol_smoke.py` for HTTP URL.
- Manual: 2 clients → ≤1 process/container for migrated server.
- Regression: `scripts/ai/mcp/check.sh` green for stdio path.

### Phase 2 — Expand + ergonomics

1. More T1/T2 servers.
2. Profile `shared` as multi-client daily recommendation on 32 GiB.
3. Grok Windows projection helper.
4. Optional single reverse-proxy.
5. Optional idle shutdown.

### Phase 3 — Hardening (optional)

1. Loopback auth token.
2. Tool-call audit (privacy review).
3. Watchdog resource budgets.
4. Detect/report Desktop Toolkit MCP still enabled.

## Security (v1)

| Rule | Detail |
| --- | --- |
| Bind | `127.0.0.1` only |
| Secrets | Env via existing loaders; never in tracked JSON |
| Isolation | Weak — same-user trust; not multi-tenant |
| Remote allowlist | Unchanged for SaaS |

## Operator UX (after implementation)

```powershell
.\scripts\ops\runtime\mcp\start-shared.ps1
$env:PYTHONPATH = (Resolve-Path .).Path
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation
# restart AI clients once
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -KillHostGateways
```

Fallback: `--profile stable --transport-mode stdio`.

### Immediate ops (today — no code)

1. Leave **one** `grok.exe` (now 6).
2. Full client restart after `apply-docker-stable-mcp -Profile stable`.
3. Docker Desktop → MCP Toolkit: disable jetbrains / node-code-sandbox / default profile (or Toolkit).
4. When AI idle: `cleanup-mcp-orphans.ps1 -KillHostGateways`.
5. Do not run Grok + Cursor + WSL-Codex all with heavy MCP.

## Risks

| Risk | Mitigation |
| --- | --- |
| Client lacks streamable HTTP | Phase 0 matrix; keep stdio |
| Bridge protocol drift | Pin version; smoke tests |
| Accidental kill of shared stack | Name/label allowlist |
| Toolkit still spawns jetbrains | Ops doc + cleanup; out of SSOT |
| #6293 regression (stdio Compose keepalive) | HTTP readiness only; no TTY fake-alive |
| Default generator surprise | Default transport remains `stdio` |

## Success metrics

1. ≥2 clients on shared server → **≤1** process/container for that server.
2. Host free RAM improved vs multi-stdio baseline under same client count.
3. No random-name thrash for migrated servers.
4. Docs + `check.sh` + smoke green; debt budgets not increased.

## PR / issue sequence

| ID | GitHub | Scope |
| --- | --- | --- |
| **ISSUE-0** | [#6563](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6563) | Umbrella program + evidence |
| **ISSUE-OPS** | [#6567](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6567) | Operator thrash playbook + optional single-client cleanup script |
| **ISSUE-P0** | [#6565](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6565) | Phase 0 matrix + `MCP_SHARED_RUNTIME.md` |
| **ISSUE-P1A** | [#6566](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6566) | Shared runtime skeleton + cleanup/ensure-stable protect |
| **ISSUE-P1B** | [#6568](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6568) | `setup_mcp --transport-mode` + localhost allowlist |
| **ISSUE-P1C** | [#6564](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6564) | First shared server MVP (host high-thrash and/or brave) |
| **ISSUE-P2** | [#6569](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6569) | Expand set, profile `shared`, apply helper, lesson/quickstart |

## Open decisions (resolve in Phase 0)

1. First shared server: host `adr-analysis`/`deja` vs `brave-search` (ROI vs client HTTP support).
2. Docker vs host for shared brave.
3. Whether Grok loads workspace HTTP entries or needs separate projection.
4. Auth: none on loopback v1 vs mandatory token.

## Relationship to prior work

- **Keep:** profiles, orphan cleanup, ensure-stable, tracked full portable SSOT.
- **Do not redo:** #6293 stdio Compose retirement — shared plane is HTTP, not stdio Compose.
- **Reinterpret “one client”:** one heavy stdio client **or** many clients on shared HTTP.

## Answers

| Question | Answer |
| --- | --- |
| Only one client may use MCP? | **No** — thrash mitigation under stdio, not a protocol limit. |
| One MCP for several clients? | **Yes** via Streamable HTTP (or existing remote HTTP). Stdio stays 1:1. |
