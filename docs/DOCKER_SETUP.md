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

Рабочий release bundle состоит из двух независимых projects:

| Stack | Project | Назначение |
| --- | --- | --- |
| `main` | `bioetl-main` | BioETL readiness endpoint |
| `monitoring` | `bioetl-monitoring` | Prometheus, Pushgateway, Grafana, renderer |

Запускайте и проверяйте каждый stack отдельно через manager. Общая сеть
`bioetl-monitoring` создаётся manager только при отсутствии. Stateful volumes
monitoring и их legacy‑имена защищены campaign evidence и не удаляются.

## Docker Desktop / WSL recovery

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
никогда не выполняет `wsl --shutdown`.

## Resource Saver и WSL memory reclaim

Resource Saver и `autoMemoryReclaim=gradual` могут быть полезны на конкретной
рабочей станции, но это operator-reviewed host settings. Автоматизация BioETL
не изменяет `.wslconfig`; включайте их только после отдельной проверки Desktop/
WSL версии, latency восстановления и отсутствия потери volumes.

## Promotion evidence

100 cycles, полный fault matrix, непрерывный 72-hour soak и 100 Desktop recovery
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
