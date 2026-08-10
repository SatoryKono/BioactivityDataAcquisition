______________________________________________________________________

Version: 1.0.0
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-04'

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

Network `bioetl-monitoring` is created by the runtime manager when starting
`main` or `monitoring` if missing — not a manual `docker network create`
prerequisite.

## Main stack (default)

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack main
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack main
```

Readiness: `http://127.0.0.1:8000/health/ready`

Readiness includes `checks.report_root` (bind-identity marker
`reports/.bioetl-report-root`). With `BIOETL_ENFORCE_REPORT_ROOT_MARKER=1`
(default in `docker-compose.yml`), a missing marker makes ready **unhealthy**
so Grafana Browse Recent Runs cannot silently read an empty stale bind.

Verify host vs container report trees:

```bash
python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay
```

`runtime_manager.py` also binds this checkout's exact `data/` and `reports/`
directories and injects a managed `BIOETL_RUNTIME_SOURCE_ID`. Check the
dashboard data-plane identity with:

```bash
curl http://127.0.0.1:8000/ops/control-plane/ready
```

The returned `runtime_source_id` must be a 64-character SHA-256 value, not
`null` or `unmanaged`. A raw `docker compose up` does not establish this
identity.

## Monitoring stack (opt-in only)

Do **not** start monitoring unless you explicitly need Grafana screenshots or
local PromQL debugging.

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack monitoring
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack monitoring
```

Grafana bootstrap (`grafana/scripts/bootstrap-datasources.sh`) always starts the
UI with Prometheus. Ops HTTP (Infinity / Run Explorer identity panels) is
provisioned only when `/ops/control-plane/ready` matches the managed
`BIOETL_RUNTIME_SOURCE_ID` within the poll budget (default 30×2s ≈ 60s). On
timeout, unmanaged id, or mismatch the default is **Prometheus-only** (deferred
Ops HTTP), not a crash loop. Status is written to
`/var/lib/grafana/bioetl-bootstrap-status.json` inside the container.

For audit/render fail-closed (require Ops HTTP or refuse to start Grafana):

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
| default surface | main (+ optional neo4j); monitoring opt-in |

Rules:

- Prefer `--no-build`; rebuild only when Dockerfile/deps actually change.
- One stack at a time; **do not** start monitoring by default.
- Keep free host RAM **≥ 4 GiB** before Docker thrash.
- Stop foreign/non-`bioetl-*` containers (ensure-stable does this unless
  `-KeepForeignContainers`).
- Do not thrash `--force-recreate` / multi-stack rebuild under low free RAM.

Agent memory anchors:

- `docs/00-project/ai/memory/agent-memory.md` (Docker / WSL section)
- `src/memory/curated/lessons/docker-desktop-wsl-stability-32gib.md`

Запрещено: `down -v`, volume/system prune, удаление VHDX/data root.

Подробнее: `docs/DOCKER_SETUP.md`.
