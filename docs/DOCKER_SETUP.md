# Локальный Docker runtime BioETL

> BIOETL_DOCKER_HELPER_ADR010_ADJUNCT — Local-Only Docker helpers governed by ADR-010.
> Contract: `configs/quality/docker_helper_contracts.yaml`

Docker в BioETL — необязательный локальный adjunct по ADR-010. Канонический
runtime проекта остаётся Python/venv; Docker не требуется для обычных тестов,
хранилища, блокировок или orchestration.

## Безопасность и границы

- Не создавайте и не изменяйте `.env` или `.env.*` в рамках этого workflow.
  Передавайте требуемые значения только в environment текущего процесса из
  одобренного локального secret store.
- Не используйте `docker compose down -v`, `docker volume prune`,
  `docker system prune`, удаление VHDX или Docker data root как способ
  восстановления.
- Не запускайте один Compose project одновременно из Windows, `/mnt/*`,
  `/tmp` и Linux runtime mirror. Поддерживается один origin на Linux filesystem.
- Все lifecycle операции выполняются через
  `scripts/ops/runtime/docker/runtime_manager.py`.

## Reviewed helper Compose adjuncts

Следующие legacy root-файлы перенесены под owner-controlled runtime path и
остаются необязательными локальными adjuncts:

| Legacy root path | Канонический путь |
| --- | --- |
| `docker-compose.alertmanager.yml` | `scripts/ops/runtime/docker/compose/alertmanager.yml` |
| `docker-compose.minio.yml` | `scripts/ops/runtime/docker/compose/minio.yml` |
| `docker-compose.redis.yml` | `scripts/ops/runtime/docker/compose/redis.yml` |
| `docker-compose.sonarqube.yml` | `scripts/ops/runtime/docker/compose/sonarqube.yml` |

В обычном workflow сеть создаёт manager. Команда
`docker network create bioetl-monitoring` не является ручным prerequisite и
приведена только как идентификатор управляемой операции.

## Предварительные условия

1. Docker Desktop установлен, WSL2 integration включена только для рабочего
   Linux distribution, а `docker info` доступен из него.
2. Репозиторий для фактического запуска находится на Linux filesystem, например
   `/home/<user>/.local/share/bioetl-runtime/BioactivityDataAcquisition2`.
3. Требуемые environment names для выбранного stack заданы в текущем процессе.
   Полный список является частью
   `configs/quality/docker_runtime_contracts.yaml`.
4. Проверка запускается до мутации:

   ```bash
   python scripts/ops/runtime/docker/runtime_manager.py check --stack main
   ```

`start` и `recover` идемпотентно создают отсутствующие contracted external
networks с owner label. Существующая сеть без owner label или с другим owner
отклоняется; manager никогда не удаляет и не пересоздаёт её автоматически.

## Поддерживаемый lifecycle

Замените `<stack>` на `main`, `monitoring`, `neo4j`, `neo4j-audit`, `redis`,
`minio`, `alertmanager` или `sonarqube`.

```bash
# Статическая и host preflight-проверка
python scripts/ops/runtime/docker/runtime_manager.py check --stack <stack>

# Идемпотентный запуск с render, readiness и stabilization gates
python scripts/ops/runtime/docker/runtime_manager.py start --stack <stack> --timeout 180

# Readiness-aware статус, а не только состояние running
python scripts/ops/runtime/docker/runtime_manager.py status --stack <stack>

# Ограниченные логи
python scripts/ops/runtime/docker/runtime_manager.py logs --stack <stack> --tail 100

# Read-only diagnostic bundle
python scripts/ops/runtime/docker/runtime_manager.py diagnose --stack <stack>

# Bounded recovery после анализа diagnostics
python scripts/ops/runtime/docker/runtime_manager.py recover --stack <stack> --timeout 180

# Остановка без удаления volumes
python scripts/ops/runtime/docker/runtime_manager.py stop --stack <stack> --timeout 60
```

Успешный `start`, `status` или `recover` означает, что обязательные services
готовы, не имеют OOM/restart/image drift и прошли stabilization. Простого
`docker ps` недостаточно.

## Release bundle

Default release surface (when Docker is used at all):

| Stack | Project | Default? | Назначение |
| --- | --- | --- | --- |
| `main` | `bioetl-main` | **Yes** | Health/metrics on `:8000` |
| `monitoring` | `bioetl-monitoring` | **No (opt-in)** | Prometheus, Pushgateway, Grafana, renderer |

**Removed:** Loki, Promtail, Tempo, Quarantine Explorer container/UI coupling.
Monitoring is no longer part of the default startup path (`docker-setup.sh start`
starts **main** only).

Запускайте stacks отдельно через manager. Сеть `bioetl-monitoring` создаётся
manager только при start monitoring/main, когда она отсутствует. Volumes
monitoring **не** удалять routine stop'ом (`stop` без `-v`).

## Docker Desktop / WSL recovery

### Preferred crash-resistant path (Windows host)

On 32 GiB Windows hosts with PyCharm + Docker Desktop, engine flaps usually
mean **host free RAM collapsed**, not a broken compose contract. Prefer:

```powershell
# Free-RAM check, dual docker info stability, stop foreign containers,
# start main without rebuild; optional Neo4j.
.\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j

# After OOM / missing npipe dockerDesktopLinuxEngine:
.\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl -WithNeo4j
```

Operator-reviewed host defaults for this class of machine (not auto-written by
repo scripts; apply once per workstation):

| Knob | Recommended |
| --- | --- |
| `%USERPROFILE%\.wslconfig` `memory` | **6 GiB** (avoid 16 GiB on 32 GiB hosts) |
| free host RAM before thrash | **≥ 4 GiB** |
| main `bioetl` mem_limit | **768 m** (health server only) |
| neo4j mem_limit / heap max | **768 m** / **384 m** |

Hard rules for agents and operators:

- Prefer `--no-build`; rebuild only when Dockerfile/deps change.
- One stack at a time; monitoring is **opt-in**.
- Never thrash `compose --force-recreate` / multi-stack rebuild under low free RAM.
- Never use `docker compose down -v`, volume prune, or VHDX deletion for recovery.
- Compose project flags: `-p bioetl-main`, `-p bioetl-neo4j`, `-p bioetl-monitoring`.
- PowerShell: do **not** name parameters `$Args` (automatic variable); use
  `$DockerArgs` in wrappers.

### Desktop diagnostic restart

Сначала соберите evidence и выполните поддерживаемый restart:

```powershell
.\scripts\ops\runtime\docker\restart-docker.ps1 `
  -TimeoutSeconds 180 `
  -ReportPath reports/quality/docker-desktop-recovery.json
```

Скрипт ограничивает каждый subprocess и общий deadline, классифицирует Desktop
capabilities, WSL/VHD, CLI/engine origins, Compose origins, port owners, bind
translation и Docker data capacity, затем пишет redacted v2 report.

Force termination не является обычным recovery. Он доступен только при
одновременном указании `-ConfirmLastResort`, точной строки
`I_UNDERSTAND_FORCE_TERMINATION_IS_DESTRUCTIVE` через
`-LastResortConfirmation` и подтверждении PowerShell `ShouldProcess`. Скрипт
`restart-docker.ps1` не выполняет `wsl --shutdown` by default; bounded WSL
reclaim is explicit via `ensure-stable.ps1 -RestartWsl`.

## Resource Saver и WSL memory reclaim

Resource Saver и `autoMemoryReclaim=gradual` могут быть полезны на конкретной
рабочей станции, но это operator-reviewed host settings. Автоматизация BioETL
не изменяет `.wslconfig` сама; operator may set a modest `memory=` cap after
checking Desktop/WSL version, recovery latency, and volume safety.

## Promotion evidence

100 cycles, полный fault matrix, непрерывный 72-hour soak и 10 Desktop recovery
trials выполняются только запланированной командой из
`docs/05-operations/runbooks/docker-image-resource-promotion.md`. Campaign
требует точный disruption token и существующий GPG signing fingerprint; он не
создаёт ключи, `.env`, volumes или host configuration.

До первой lifecycle-мутации campaign требует наличие всех target volumes из
`migration.volume_map` и записывает каждый legacy volume как `present` либо
`not_applicable`. Отсутствующий target volume останавливает новый campaign до
отдельно одобренной migration-процедуры.

См. также:

- `docs/DOCKER_QUICKSTART.md`
- `docs/05-operations/runbooks/docker-stability.md`
- `docs/05-operations/runbooks/codex-wsl-docker-sandbox-troubleshooting.md`
- `docs/05-operations/runbooks/docker-compose-project-migration.md`
