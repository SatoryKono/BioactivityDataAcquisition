______________________________________________________________________

Version: 1.0.0
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-13'

______________________________________________________________________

# Docker quick start

> **Classification:** repo-only adjunct guide (outside MkDocs nav). Path is
> stable for architecture/docker helper contracts. Docs audit cycle 2 / #7430.
>
> BIOETL_DOCKER_HELPER_ADR010_ADJUNCT — Local-Only Docker helpers governed by ADR-010.
> Contract: `configs/quality/docker_helper_contracts.yaml`

Docker — optional local adjunct. Канонический runtime: Python/venv.
Выполняйте команды из Linux filesystem mirror, не из `WSL-mounted Windows paths` или `/tmp`,
и не создавайте/не изменяйте `.env`.

## Default release surface

| Stack | Default? | Назначение |
| --- | --- | --- |
| `main` (`bioetl-main`) | **Yes** (if Docker used) | Health/metrics endpoint only (`:8000`) |
| `neo4j` | Optional helper | Graph store |
| `monitoring` (`bioetl-monitoring`) | **No** — opt-in only | Prometheus, Pushgateway, Grafana, renderer |

**Removed from shipping Docker surface:** Loki, Promtail, Tempo, Quarantine Explorer
HTTP UI (`quarantine serve` / Infinity datasource / Silver Reject Explorer dashboard).

Domain quarantine write-path inside BioETL pipelines remains (Medallion DQ);
only the **operator Explorer UI + Loki/Tempo stacks** were deleted.

## Network preconditions (MEDIUM)

Shared Docker networks use a **fixed `name:`** and owner label
(`com.bioetl.owner`). They are **not** declared as `external: true` in compose:
`docker compose up` **creates** missing nets (or reuses existing ones). Prefer
`ensure-networks` / `ensure-stable` after a wipe so labels are correct before
first up.

Which compose file attaches to which shared network:

| Compose file | Networks |
| --- | --- |
| `docker-compose.monitoring.yml` | **`bioetl-monitoring` only** |
| `docker-compose.yml` (main) | **`bioetl-monitoring` + `bioetl-runtime`** |
| `docker-compose.neo4j.yml` | **`bioetl-runtime`** |

| Precondition | Why | How to satisfy |
| --- | --- | --- |
| Owner label on shared nets | reject foreign networks | compose labels / `runtime_manager` / `--ensure` |
| Container `bioetl` on `bioetl-monitoring` | scrape + Ops HTTP | start **main** so bioetl joins monitoring |

### Full reinstall / network wipe guarantee

After Docker Desktop reinstall, `docker network prune`, or a clean engine, shared
nets may be **absent**. Do **not** rely on “they already exist on this machine”.

**SSOT ensure (creates missing nets with `com.bioetl.owner`, never deletes):**

```bash
# Preferred — all contracted shared networks (monitoring + runtime):
python scripts/ops/runtime/docker/runtime_manager.py ensure-networks --stack main

# Equivalent checker (read-only without --ensure):
python scripts/ops/runtime/docker/check_network_preconditions.py --stack all --ensure
```

**Windows one-shot after wipe** (engine harden + ensure nets + main):

```powershell
.\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j
```

`ensure-stable` calls `runtime_manager ensure-networks` first; if Python is
unavailable it falls back to `docker network create` with the same owner label
and **exits non-zero** if create fails.

**Windows PowerShell from the repository root** uses one self-contained
entrypoint. It selects `.venv-win`, imports the root environment into the
current process through the shared `load_repo_env.ps1` loader, and never writes
an `.env` file. Values already present in the process take precedence over file
values.

```powershell
.\scripts\ops\docker-setup.ps1 ensure-networks main
.\scripts\ops\docker-setup.ps1 start main
# monitoring remains opt-in:
.\scripts\ops\docker-setup.ps1 start monitoring
.\scripts\ops\docker-setup.ps1 status monitoring
.\scripts\ops\docker-setup.ps1 grafana-preflight
```

A failed `start` or `recover` keeps its non-zero exit and prints a bounded JSON
summary with `action`, `stack`, `primary_cause`, and the redacted incident
`report` path. Use the report for diagnosis; credentials are never passed on
the command line or included in that summary.

Then start stacks as usual:

```bash
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
# optional:
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring --timeout 180
```

Raw `docker compose -f docker-compose.monitoring.yml up` also **creates**
`bioetl-monitoring` if missing (named network, not external). Prefer
`ensure-networks` or `runtime_manager start` so owner labels stay contracted.

## PromQL rule syntax gate (before load)

Shipped rules under `grafana/prometheus-rules/*.yml` are validated **before**
Prometheus loads them:

1. **Structural** — every `alert`/`record` has a non-empty `expr`
2. **`promtool check rules`** — real PromQL + rule schema (local `promtool` or
   pinned Docker image `prom/prometheus:v3.13.1@…`)

Wired into:

- `runtime_manager check|start --stack monitoring` (preflight finding
  `MONITORING_PROMQL_SYNTAX` / `MONITORING_RULE_EXPR_MISSING`)
- CI: `python -m scripts.engineering.qa check-prometheus-rules --runner docker`

```bash
export PYTHONPATH=.
python -m scripts.engineering.qa check-prometheus-rules --runner docker
```

If neither `promtool` nor Docker is available, preflight emits warning
`MONITORING_PROMQL_TOOL_MISSING`. Fail closed with `BIOETL_REQUIRE_PROMTOOL=1`.

### Rule write conflicts + Prometheus memory

Same-timestamp ingest WARNs
(`Error on ingesting results from rule evaluation with different value but same timestamp`)
drop samples and inflate WAL/head churn. Prevention:

1. **Identity uniqueness gate** — `check-prometheus-rules` fails if two
   `record:` rules share the same metric name **and** the same static `labels:`
   (distinct labels like `reason=` are OK).
2. **Slower evaluation** — dashboard monogroup + alerts use `interval: 30s`
   (global `evaluation_interval: 30s`) to cut concurrent write pressure.
3. **Memory budget** — `mem_limit: 3g`, `GOMEMLIMIT=2500MiB`, `GOGC=50`,
   TSDB retention **7d / 2GB**, `query.max-concurrency=2`.

```bash
# After compose change, recreate Prometheus (limits do not hot-reload):
docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml up -d --force-recreate prometheus
```

Live container still showing **10 GiB** limit means it was started from an old
compose — recreate is required.

### Partial rule errors (silent metric gaps)

Prometheus **stays up** when individual rules fail evaluation or groups miss
iterations — affected recording series simply stop updating. BioETL surfaces this:

| Signal | Purpose |
| --- | --- |
| `bioetl_prometheus_rule_evaluation_failures_10m` | count of eval failures |
| `bioetl_prometheus_rule_iterations_missed_10m` | missed group iterations |
| `bioetl_prometheus_rule_partial_error_active_10m` | bool any partial error |
| Alert `BioETLPrometheusRuleEvaluationFailures` | warning after 5m |
| Alert `BioETLPrometheusRuleIterationsMissed` | warning after 10m |
| Live `/api/v1/rules` lastError scan | fail closed on health=err |

```bash
# After monitoring is up — fails if any BioETL rule has lastError or recent failures:
python scripts/ops/observability/check_prometheus_rules_health.py --json
# Included in:
python scripts/ops/observability/validate_live_observability.py
```

## Main stack (default)

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack main
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack main
```

Readiness: `http://127.0.0.1:8000/health/ready`

Readiness includes `checks.report_root` with two independent checks:

- tracked layout marker `reports/.bioetl-report-root`;
- ignored machine-local source attestation
  `reports/.bioetl-report-source.json`.

With `BIOETL_ENFORCE_REPORT_ROOT_MARKER=1` (default in
`docker-compose.yml`), either an invalid layout or a source identity that does
not match `BIOETL_RUNTIME_SOURCE_ID` makes ready **unhealthy**. The source
attestation is written atomically by `runtime_manager start|recover --stack
main`; raw `docker compose up` remains unmanaged and fails closed.

Verify host vs container report trees:

```bash
python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay
```

`/health/ready` green is not enough for **Inspect Recent Runs**. After switching
worktrees, run the verifier from the checkout you are viewing. Do not start
`--stack main` from `/tmp/bioetl-issues*` unless you pass
`--allow-transient-origin`; leftover issue worktrees steal the global `bioetl`
container. `runtime_manager status --stack main` now re-runs the same bind gate.

`runtime_manager.py` binds the explicitly selected `data/` and `reports/`
directories and injects a managed `BIOETL_RUNTIME_SOURCE_ID`. Absolute Windows,
WSL (`/mnt/<drive>/...`), and Docker Desktop host path spellings normalize to
one comparison identity; transient `docker-desktop-bind-mounts/<hash>` origins
remain rejected. Check the dashboard data-plane identity with:

```bash
curl http://127.0.0.1:8000/ops/control-plane/ready
```

The returned `runtime_source_id` must be a 64-character SHA-256 value, not
`null` or `unmanaged`. A raw `docker compose up` does not establish this
identity. `runtime_manager check|status` reports
`DASHBOARD_REPORT_SOURCE_IDENTITY` for a missing/foreign attestation;
`start|recover` materializes the intended identity before preflight and then
the post-start verifier confirms it end to end.

Identity resolution is deterministic and fail-closed. Precedence is computed
runtime root → process environment → repository env loader → container
environment → container label. Diagnostics classify the independently checked
layout marker and identity as `missing`, `invalid`, `foreign`, or `aligned`;
an invalid higher-precedence candidate is never replaced by a lower one.

## Monitoring stack (opt-in only)

Do **not** start monitoring unless you explicitly need Grafana screenshots or
local PromQL debugging.

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack monitoring
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack monitoring
```

Grafana bootstrap (`grafana/scripts/bootstrap-datasources.sh`) **always** starts
the UI with Prometheus (provisioned *before* any Ops wait). Ops HTTP (Infinity /
Run Explorer identity panels) is provisioned only when
`/ops/control-plane/ready` matches the managed `BIOETL_RUNTIME_SOURCE_ID`.

| Mode | Poll budget | On timeout / mismatch |
| --- | --- | --- |
| **Soft (default)** `REQUIRE_OPS_HTTP=0` | **5×1s ≈ 5s** | Prometheus-only, `exec /run.sh` (no crash) |
| **Fail-closed** `REQUIRE_OPS_HTTP=1` | 30×2s ≈ 60s | `exit 1` (audit/render only) |

Unmanaged / non-hex identity skips the wait entirely. Status:
`/var/lib/grafana/bioetl-bootstrap-status.json` inside the container.

A long 60s soft wait was a common restart thrash: bioetl late → bootstrap
blocks → Grafana healthcheck fails → restart → repeat. Soft mode no longer does
that.

For audit/render fail-closed:

```bash
export BIOETL_GRAFANA_REQUIRE_OPS_HTTP=1
```

Optional poll tuning: `BIOETL_GRAFANA_OPS_READY_ATTEMPTS`,
`BIOETL_GRAFANA_OPS_READY_SLEEP_SEC`.

Stop without deleting volumes:

```bash
python scripts/ops/runtime/docker/runtime_manager.py stop --stack monitoring --timeout 60
```

## Reviewed helper Compose adjuncts

| Legacy root path | Канонический путь |
| --- | --- |
| `docker-compose.alertmanager.yml` | `scripts/ops/runtime/docker/compose/alertmanager.yml` |
| `docker-compose.minio.yml` | `scripts/ops/runtime/docker/compose/minio.yml` |
| `docker-compose.redis.yml` | `scripts/ops/runtime/docker/compose/redis.yml` |
| `docker-compose.sonarqube.yml` | `scripts/ops/runtime/docker/compose/sonarqube.yml` |

## Logs, diagnostics, recovery, stop

```bash
python scripts/ops/runtime/docker/runtime_manager.py logs --stack main --tail 100
python scripts/ops/runtime/docker/runtime_manager.py diagnose --stack main
python scripts/ops/runtime/docker/runtime_manager.py recover --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py stop --stack main --timeout 60
```

Desktop/WSL recovery:

```powershell
.\scripts\ops\runtime\docker\restart-docker.ps1 -TimeoutSeconds 180
```

If `DockerDesktop/Wsl/CommandTimedOut`: run `wsl --shutdown`, start Docker Desktop,
wait until `docker info` is stable, then retry **one** stack at a time.

### Stability (Windows / Docker Desktop)

Typical crash pattern on 32 GiB hosts: **host free RAM < 4 GiB** while WSL was
capped too high (16 GiB) and IDE + multi-stack `--build` run together. Engine
pipe (`dockerDesktopLinuxEngine`) disappears; `docker-desktop` WSL shows
**Stopped**.

Crash-resistant path (preferred):

```powershell
# One-shot: harden Desktop settings + .wslconfig, start main (+ neo4j).
.\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j

# After OOM / pipe gone:
.\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl -WithNeo4j

# Permanent host harden + auto-recover every 5 min (Task Scheduler):
.\scripts\ops\runtime\docker\harden-desktop-host.ps1 -RegisterWatchdog

# MCP container thrash (duplicate mcp/brave-search, grafana, gateways):
.\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1 -Profile stable -WithNeo4j
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -IncludeGatewayHint

# Report-only host reset (orphans / optional extra grok) — never kills bioetl-*:
.\scripts\ops\runtime\docker\reset-mcp-host-sessions.ps1
# Apply: -Execute -KillHostGateways [-KillExtraGrok]

# Multi-client shared HTTP plane (one process per migrated server):
.\scripts\ops\runtime\mcp\start-shared.ps1
.\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1 -Profile shared -TransportMode shared -WithSharedMcp -SkipEnsureStable
.\scripts\ops\runtime\mcp\health-shared.ps1
.\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1 -DisableDockerGateways
# Then FULL restart AI clients once (Grok/Cursor/Codex/Gemini/VS Code).
# Operator detail: scripts/ops/runtime/mcp/OPERATOR.md
```

`harden-desktop-host.ps1` sets Resource Saver effectively off
(`AutoPauseTimeoutSeconds=604800`), AutoStart on, Extensions/AI off, and
`.wslconfig memory=6GB`. The watchdog re-runs soft/hard ensure when the
engine pipe dies (rate-limited; refuses hard restart if free RAM &lt; 3 GiB).

Docker-backed MCP servers spawn **one container per AI session** under stdio.
Use MCP profile `stable` (no gateway/`docker run` MCP) on 32 GiB hosts, **or**
the shared Streamable HTTP plane (`start-shared` + `--profile shared
--transport-mode shared`) so multiple clients share one process per migrated
server (catalog v2: brave, adr, deja, context7, ast-grep, docker, mermaid,
dockerhub, github, fetch, prometheus, grafana; neo4j-* optional). Keep tracked
`.mcp.json` full portable stdio SSOT. Do **not** use Compose `container_name`
as the multi-client strategy (optional Mode B only; see MCP_SHARED_RUNTIME).
See `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`,
`docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`, and
`scripts/ops/runtime/mcp/OPERATOR.md`.

Hardening defaults on this host class:

| Knob | Value |
| --- | --- |
| `%USERPROFILE%\.wslconfig` `memory` | **6 GiB** (not 16) |
| main `bioetl` mem_limit | **768 m** (health server only) |
| neo4j mem_limit / heap max | **768 m** / **384 m** |
| monitoring `prometheus` mem_limit | **3 g** + `GOMEMLIMIT=2500MiB` (was 10 g unbounded) |
| monitoring Prom evaluation | **30 s** groups (was 15 s monogroup thrash) |
| monitoring `grafana` mem_limit | **2 g** (was 7.5 g) |
| monitoring `renderer` mem_limit | **3 g** (was 15 g); concurrency **1** (was 2) |
| monitoring `pushgateway` mem_limit | **512 m** (was 2.5 g) |
| monitoring peak cgroup budget | **~8.5 g** (not ~32 g) |
| grafana ↔ renderer | no hard `depends_on` health gate |
| runtime_manager wait | **prom+pgw+grafana** only; renderer optional |
| renderer health `start_period` | **45s** (was 180s) |
| default surface | main (+ optional neo4j); monitoring opt-in |

Rules:

- Prefer `--no-build`; rebuild only when Dockerfile/deps actually change.
- One stack at a time; **do not** start monitoring by default.
- Keep free host RAM **≥ 4 GiB** before Docker thrash.
- Stop foreign/non-`bioetl-*` containers (ensure-stable does this unless
  `-KeepForeignContainers`).
- Do not thrash `--force-recreate` / multi-stack rebuild under low free RAM.
- Grafana UI does **not** wait for renderer (screenshots are best-effort).
- **Renderer failure recovery** (tertiary cause: dependency without recovery):
  1. Screenshots are bounded via `GF_RENDERING_RENDERING_TIMEOUT` (default **60s**).
     Renderer skips network-idle wait and gives up on lingering queries after **12s**
     so table `d-solo` does not hang on Grafana Live.
  2. Explicit recovery SSOT (never restarts Grafana):
     ```bash
     export PYTHONPATH=.
     python scripts/ops/observability/grafana/recover_renderer.py
     # or lifecycle:
     python -m scripts.ops.runtime.docker.runtime_manager recover-renderer --stack monitoring
     # Windows:
     # .\scripts\ops\observability\grafana\recover_renderer.ps1
     ```
  3. Check only: `python scripts/ops/observability/grafana/recover_renderer.py --check-only`
  4. If OOMKilled: free ≥4 GiB RAM, then re-run recover; after 3 failures
     renderer stays down (`restart: on-failure:3`) by design — **call recover**,
     do not restart Grafana.
  5. Live still on **15 GiB / unless-stopped** means old compose — recreate:
     `docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml up -d --force-recreate --no-deps renderer`

Agent memory anchors:

- `docs/00-project/ai/memory/agent-memory.md` (Docker / WSL section)
- `src/memory/curated/lessons/docker-desktop-wsl-stability-32gib.md`

Запрещено: `down -v`, volume/system prune, удаление VHDX/data root.

Подробнее: `docs/DOCKER_SETUP.md`.
