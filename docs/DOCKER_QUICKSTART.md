# Docker quick start

> BIOETL_DOCKER_HELPER_ADR010_ADJUNCT — Local-Only Docker helpers governed by ADR-010.
> Contract: `configs/quality/docker_helper_contracts.yaml`

Docker — optional local adjunct. Канонический runtime: Python/venv.
Выполняйте команды из Linux filesystem mirror, не из `/mnt/*` или `/tmp`,
и не создавайте/не изменяйте `.env`.

## Default release surface

| Stack | Default? | Назначение |
| --- | --- | --- |
| `main` (`bioetl-main`) | **Yes** (if Docker used) | Health/metrics endpoint only (`:8000`) |
| `neo4j` | Optional helper | Graph store |
| `monitoring` | **No** — opt-in only | Prometheus, Pushgateway, Grafana, renderer |

**Removed from shipping Docker surface:** Loki, Promtail, Tempo, Quarantine Explorer
HTTP UI (`quarantine serve` / Infinity datasource / Silver Reject Explorer dashboard).

Domain quarantine write-path inside BioETL pipelines remains (Medallion DQ);
only the **operator Explorer UI + Loki/Tempo stacks** were deleted.

## Main stack (default)

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack main
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack main
```

Readiness: `http://127.0.0.1:8000/health/ready`

## Monitoring stack (opt-in only)

Do **not** start monitoring unless you explicitly need Grafana screenshots or
local PromQL debugging.

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack monitoring
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py status --stack monitoring
```

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

Typical crash pattern on 32 GiB hosts: **host free RAM < 3 GiB** while WSL
was capped at 16 GiB and IDE + multi-stack `--build` run together. Engine pipe
(`dockerDesktopLinuxEngine`) disappears; `docker-desktop` WSL distro shows
**Stopped**.

Crash-resistant path:

```powershell
# Applies host free-RAM check, waits for stable engine, starts main without rebuild.
# Stops leftover monitoring containers unless -WithMonitoring.
.\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j

# After OOM / pipe gone:
.\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl -WithNeo4j
```

Rules:

- Prefer `--no-build`; rebuild images only when Dockerfile/deps actually change.
- One stack at a time; **do not** start monitoring by default.
- Keep `%USERPROFILE%\.wslconfig` `memory=` modest (8 GiB recommended on 32 GiB hosts).
- Do not thrash `--force-recreate` / multi-stack rebuild under low free RAM.

Запрещено: `down -v`, volume/system prune, удаление VHDX/data root.

Подробнее: `docs/DOCKER_SETUP.md`.
