______________________________________________________________________

Version: 6.4.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-28'

______________________________________________________________________

# Running Pipelines

Руководство по запуску и управлению ETL-пайплайнами в BioETL.

**Версия:** 6.4.0
**Дата обновления:** 2026-04-28

> **Boundary:** this guide owns execution and runtime control flow. For initial
> environment bootstrap use [Quick Start](quick-start.md) or
> [Getting Started](getting-started.md). For operator incident handling use
> [Operations Runbooks](../05-operations/runbooks/index.md). For CLI command
> reference, see [CLI Reference](../04-reference/cli.md). For declarative workflow
> inventory, see [Workflow Catalog](../04-reference/workflow-catalog.md).

______________________________________________________________________

## Prerequisites

1. **Используется поддерживаемый bootstrap path:**

   ```bash
   # CI / single-OS checkout
   uv sync --extra dev --extra tests --extra tracing
   uv run python -m scripts.ops setup-plugins
   ```

   ```powershell
   # Mixed Windows + WSL checkout: PowerShell
   .\scripts\engineering\dev\setup_env_windows.ps1
   ```

   ```bash
   # Mixed Windows + WSL checkout: WSL/Linux
   bash scripts/engineering/dev/setup_env_wsl.sh
   ```

1. **Environment настроен** (`.env` файл или переменные окружения)

1. **Bootstrap проверен локальным smoke/stable run:**

   ```bash
   # Smoke / stable local verification
   uv run python -m scripts.engineering.dev run-tests smoke
   ```

   Канонический bootstrap — `uv sync` / `make install`; `scripts/engineering/dev/dev_setup.sh` **удалён** и не является
   поддерживаемым bootstrap path.

> **Note:** BioETL использует **Local-Only** архитектуру (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) **не требуются**.

______________________________________________________________________

## Быстрый старт

```bash
# Список доступных пайплайнов
bioetl config list-pipelines

# Запуск пайплайна с ограничением (для тестирования)
bioetl run --pipeline chembl_activity --limit 100

# Запуск полного пайплайна
bioetl run --pipeline chembl_activity

# Инспекция control-plane артефактов завершённого запуска
bioetl run-manifest show <RUN-ID>
```

Для mixed Windows + WSL checkout можно вызывать CLI через OS-specific
интерпретатор без явной активации окружения:

```powershell
.\.venv-win\Scripts\python.exe -m bioetl run --pipeline chembl_activity --limit 100
```

```bash
"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m bioetl run --pipeline chembl_activity --limit 100
```

### Run Manifest и Run Ledger

Если `settings.pipeline.control_plane.run_manifest_enabled=true`, каждый запуск
создаёт immutable manifest до начала фактического выполнения пайплайна. Если
дополнительно включён `run_ledger_enabled`, runtime пишет append-only историю
lifecycle и artifact publication events, связанную через `manifest_id`.

Минимальный static control-plane contract задаётся через
`settings.pipeline.control_plane.required_persistence_profile`:

- `replay_ready` — default floor for executable runs; runtime требует
  `run_manifest_enabled=true` и execution
  context внутри опубликованной strict exact-replay support boundary;
- `degraded_observable` — explicit local diagnostic opt-down for
  non-`--exact-replay`, non-critical launches that must remain observable
  without claiming the `replay_ready` evidence floor; it is no longer the
  default floor for executable runs;
- `forensic_grade` — runtime требует и `run_manifest_enabled=true`, и
  `run_ledger_enabled=true`, и replay-ready / lineage-closure surfaces внутри
  той же опубликованной boundary.

Для локального live/backfill запуска, который должен остаться observable, но
не заявлять `replay_ready` evidence floor, используйте per-run override:

```bash
bioetl workflow run chembl_publication --limit 1000 --required-persistence-profile degraded_observable
```

`--exact-replay` всё равно повышает degraded override обратно к strict
published family default, поэтому этот флаг не является обходом exact-replay
guardrails.

HTTP identity helpers for Grafana (`ID` / control-plane selectors) are served by
the main **`bioetl health server`** (default **`:8000`**, datasource
**BioETL Ops HTTP**). CLI default does **not** auto-start any detached
observability backend (`--ensure-observability-backend` is off). Quarantine
Explorer / `quarantine serve` on `:8081` is not part of the shipping surface.
Optional opt-in: `--ensure-observability-backend` starts `bioetl health server`
on `--observability-backend-port` (default 8000).

Для inspection используются команды:

```bash
bioetl run-manifest show <RUN-ID|MANIFEST-ID>
bioetl run-manifest diff <LEFT> <RIGHT>
bioetl run-manifest verify <LEFT> <RIGHT>
bioetl run-manifest forensic-diff <LEFT> <RIGHT>
bioetl diagnostics forensic-diff <LEFT> <RIGHT>
```

`run-manifest diff` exposes a `forensic_diff` / `cross_surface_replay_diff`
section for manifest, effective-config, checkpoint-anchor, lineage, input
snapshot, and planned-artifact drift. New manifests also surface
`dependency_lock_hash` when a repository lockfile is available.
Use `run-manifest verify` when automation must fail closed on missing
effective-config replay evidence. Use `forensic-diff` when the operator-facing
report must also include replay
capability, exact-replay blockers, artifact/sidecar completeness, lineage
closure status, and missing-evidence classification.

Файловое MVP-хранилище control-plane лежит в:

```text
data/output/control/run_manifest/{manifest_id}.json
data/output/control/run_ledger/{manifest_id}.jsonl
```

Sidecar metadata Bronze/Silver/Gold не встраивает полный manifest payload, но
несёт ссылку `runtime.manifest_id` для связи dataset -> run control plane.

______________________________________________________________________

## Типы запуска (Run Types)

| Тип             | Флаг                  | Описание                                        | Очистка данных |
| --------------- | --------------------- | ----------------------------------------------- | -------------- |
| **Incremental** | (по умолчанию)        | Обработка новых записей с последнего checkpoint | Нет            |
| **Backfill**    | `--run-type backfill` | Обработка записей для заполнения пробелов       | Silver/Gold    |
| **Rebuild**     | `--run-type rebuild`  | Полная перезагрузка производных данных          | Silver/Gold    |

### Incremental Run

Обрабатывает только новые записи с момента последнего успешного запуска:

```bash
bioetl run --pipeline chembl_activity
```

### Backfill Run

Заполняет пробелы в данных. Требует подтверждения (очищает Silver/Gold):

```bash
# С подтверждением
bioetl run --pipeline chembl_activity --run-type backfill

# Без подтверждения
bioetl run --pipeline chembl_activity --run-type backfill --yes

# Предпросмотр очистки
bioetl run --pipeline chembl_activity --run-type backfill --dry-run
```

### Full Rebuild

Полная перезагрузка производных данных. Очищает Silver/Gold и заново строит их из доступного Bronze:

```bash
# С подтверждением
bioetl run --pipeline chembl_activity --run-type rebuild

# Без подтверждения
bioetl run --pipeline chembl_activity --run-type rebuild --yes

# Предпросмотр очистки
bioetl run --pipeline chembl_activity --run-type rebuild --dry-run
```

______________________________________________________________________

## Тестирование и разработка

### Ограничение количества записей

Для тестирования ограничьте количество обрабатываемых записей:

```bash
bioetl run --pipeline chembl_activity --limit 100
```

### Resume (продолжение прерванного запуска)

Если пайплайн был прерван, продолжите с checkpoint:

```bash
bioetl run --pipeline chembl_activity --resume
```

Если оператору нужен не mutable latest pointer, а конкретный historical
occurrence, используйте explicit selector:

```bash
bioetl run --pipeline chembl_activity --resume-run-id 7f26d7b2-2c25-4aef-bf4c-030e4f8a4f87
bioetl run --pipeline chembl_activity --resume-manifest-id manifest-parent-001
```

`--resume` означает восстановление из checkpoint state, а не strict exact replay.
Чтобы не смешивать operator semantics:

| Surface                                | Что означает                                                                                                        | Что не означает                                                    |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `--resume`                             | Продолжить прерванный запуск из checkpoint state с compatibility checks                                             | Не публикует новый run как exact replay родительского run          |
| `--resume-run-id` / `--resume-manifest-id` | Привязать ordinary-pipeline resume к одному конкретному historical checkpoint occurrence                             | Не обходят compatibility anchors и не превращают run в exact replay |
| `--run-type rebuild`                   | Пересчитать производные слои заново из доступного source-of-truth/Bronze                                            | Не использует checkpoint continuation и не доказывает exact replay |
| `--exact-replay`                       | Запросить strict exact replay на snapshot-backed inputs внутри опубликованной support boundary с fail-closed policy | Не является обычным resume или обычным rebuild                     |
| `replay_mode=same_data_state_recovery` | Inspection-классификация run, у которого есть immutable snapshots и same-data-state recovery anchors                | Не отдельный CLI flag                                              |

Resume-совместимость checkpoint управляется через
`settings.pipeline.control_plane.checkpoint_compatibility_policy`:

- `observe` — degraded operator mode: допускает только non-identity degraded
  warnings, но canonical execution-identity mismatch всё равно блокирует
  resume.
- `soft_fail` (default) — заблокировать resume при несовместимости без падения процесса.
- `hard_fail` — завершить запуск ошибкой при несовместимости checkpoint/runtime identity.

Policy применяется к execution identity checkpoint, включая effective config hash
и execution fingerprint.

Machine-readable checkpoint load statuses distinguish:

- `observe_blocked_identity` — `observe` mode still blocked resume because the
  canonical execution identity mismatched.
- `observe_loaded_degraded` — `observe` mode resumed only after a non-identity
  compatibility warning.

Supported resume modes:

- ordinary `bioetl run --resume` uses the latest checkpoint pointer and
  compatibility checks without ledger suffix replay;
- ordinary `bioetl run --resume-run-id` / `--resume-manifest-id` uses the same
  compatibility enforcement but pins the checkpoint load to one explicit run
  occurrence for forensic/debug workflows;
- composite `bioetl run-composite --resume` uses checkpoint snapshot state as
  the base and then replays ledger events strictly after `last_event_id`.

For both modes, the canonical compatibility anchor is
`execution_fingerprint`. Composite-specific occurrence metadata can still be
diagnostic evidence, but it must not override a matching canonical execution
identity.

### Debug логирование

```bash
bioetl run --pipeline chembl_activity --debug
```

### Bronze Cache (use-cached-bronze)

BioETL поддерживает запуск пайплайнов на основе локального кеша Bronze-слоя вместо выполнения HTTP-запросов к API. Это полезно для быстрой отладки трансформаций и тестирования DQ-правил на ранее загруженных данных.

> **Note:** Опция `--use-cached-bronze` **выключена по умолчанию**.
> Для запуска из кеша явно укажите флаг `--use-cached-bronze`.

```bash
# Использовать кеш Bronze-слоя
bioetl run --pipeline chembl_activity --use-cached-bronze

# Принудительно запросить свежие данные из API
bioetl run --pipeline chembl_activity --no-cached-bronze

# Фильтрация кеша по дате
bioetl run --pipeline chembl_activity --cached-bronze-date 2026-01-20

# Указание кастомного пути к кешу
bioetl run --pipeline chembl_activity --cached-bronze-path ./my-cache
```

Если пользователь запрашивает `bioetl run --exact-replay` без
`--use-cached-bronze`, CLI теперь заранее предупреждает, что такой запуск
находится **вне strict exact-replay boundary**. Exact replay для ordinary
pipeline path по-прежнему требует snapshot-backed cached Bronze inputs.

Runtime validation for supported ordinary exact replay is test-backed by
`tests/integration/ci/test_track_d_fixture_control_plane_linkage.py`. A passing
validation run proves that two occurrences over the same immutable cached
Bronze snapshot keep the same `execution_fingerprint`,
`effective_config_artifact_id`, `effective_config_hash`, DQ compatibility hash,
and input snapshot IDs while `run_id` and `manifest_id` remain occurrence-only.

### Фильтрация по CSV

Обрабатывать только записи с указанными ID:

```bash
bioetl run --pipeline chembl_activity \
    --input-csv data/filter-ids.csv \
    --filter-column molecule_id \
    --filter-field molecule_id
```

______________________________________________________________________

## Конфигурация пайплайнов

Стандартные пайплайны настраиваются через **YAML-файлы** в `configs/entities/`, composite-пайплайны — в `configs/composites/`:

```
configs/
├── base/
│   ├── pipeline.yaml         # Базовые pipeline/filter defaults
│   └── quality.yaml          # Базовые DQ defaults
├── providers/
│   └── {provider}.yaml       # source + provider quality/filters
├── entities/
│   └── {provider}/{entity}.yaml  # unified entity config
└── composites/
    └── {entity}.yaml         # composite pipelines
```

### Просмотр конфигурации

```bash
# Показать конфигурацию пайплайна
bioetl config show chembl_activity

# В формате JSON
bioetl config show chembl_activity --format json

# Валидация конфигурации
bioetl config validate chembl_activity
```

### Структура YAML-конфига

Минимальный unified entity config:

```yaml
version: "1.0.0"
provider: chembl
entity: activity

pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  business_primary_keys: [activity_id]

quality:
  field_validations:
    - field: standard_value
      type: range
      min: 0
      nullable: true
```

> **Подробнее:** [Pipeline Configuration Guide](pipeline-configuration.md)

______________________________________________________________________

## Блокировки (Locking)

BioETL использует **in-memory блокировки** для предотвращения concurrent writes.

> **Архитектура:** In-memory locks достаточны для Local-Only deployment (ADR-010).
> Redis **не требуется**.

### Диагностика lock state

```bash
bioetl lock check --pipeline chembl_activity --run-id <UUID>
```

`bioetl lock check` и `bioetl lock release` работают только с `MemoryLock`,
созданным в **текущем процессе CLI**. Эти команды полезны для локальной
диагностики и тестовых сценариев, но не являются cross-process интерфейсом
администрирования блокировок.

### Восстановление после зависшего процесса

Если пайплайн завершился аварийно и следующий запуск не может получить lock:

1. Убедитесь, что другой локальный процесс `bioetl` или `python` для этого пайплайна действительно не выполняется.

1. Если процесс завис, завершите именно этот процесс на уровне ОС.

1. Запустите пайплайн повторно:

   ```bash
   bioetl run --pipeline chembl_activity
   ```

1. Используйте `bioetl lock release ...` только если вы отлаживаете lock state в том же процессе, где lock был создан.

### TTL и Heartbeat

- **Default TTL:** 90 секунд
- **Heartbeat interval:** 30 секунд (автоматически продлевает блокировку)
- При аварийном завершении блокировка автоматически освобождается по истечении TTL

______________________________________________________________________

## Мониторинг и метрики

### Log Levels

```bash
# Via флаг
bioetl run --pipeline chembl_activity --debug

# Via переменную окружения
export BIOETL_LOG_LEVEL=DEBUG
bioetl run --pipeline chembl_activity
```

| Уровень   | Использование               |
| --------- | --------------------------- |
| `DEBUG`   | Разработка, troubleshooting |
| `INFO`    | Production (default)        |
| `WARNING` | Только предупреждения       |
| `ERROR`   | Только ошибки               |

### Prometheus Metrics

BioETL автоматически собирает метрики выполнения:

```bash
# Метрики доступны на порту 8000
curl http://localhost:8000/metrics | grep bioetl_
```

**Ключевые метрики:**

| Метрика                               | Тип       | Описание                          |
| ------------------------------------- | --------- | --------------------------------- |
| `bioetl_pipeline_duration_seconds`    | Histogram | Длительность выполнения пайплайна |
| `bioetl_records_processed_total`      | Counter   | Количество обработанных записей   |
| `bioetl_errors_total`                 | Counter   | Количество ошибок                 |
| `bioetl_batch_size_records`           | Histogram | Размер батчей                     |
| `bioetl_dq_records_quarantined_total` | Counter   | Карантинные записи                |
| `bioetl_circuit_breaker_state`        | Gauge     | Состояние Circuit Breaker         |

**Включение/отключение метрик:**

```bash
# Включить (по умолчанию)
export BIOETL_METRICS_ENABLED=true

# Отключить
export BIOETL_METRICS_ENABLED=false
```

> **Подробнее:** [Metrics & Monitoring Guide](metrics-monitoring.md)

### Health Server

При выполнении пайплайна доступен HTTP health server:

```bash
# Docker main / Grafana Ops HTTP identity: :8000
bioetl run --pipeline chembl_activity --health-port 8000

# Отключить
bioetl run --pipeline chembl_activity --no-health-server
```

**Endpoints:**

- `GET /health` — общий статус
- `GET /health/live` — liveness probe
- `GET /health/ready` — readiness probe

### Standalone Health Server

```bash
bioetl health server --host 0.0.0.0 --port 8000
```

> Примечание: Grafana identity panels use datasource **BioETL Ops HTTP** →
> health server (`http://bioetl:8000` in compose, or host override via
> `BIOETL_OPS_HTTP_URL`). Record-level quarantine forensics use CLI
> `bioetl quarantine inspect`, not a Grafana explorer.

______________________________________________________________________

## Выходные данные (Pipeline Output)

Пайплайны записывают данные в три слоя (Medallion Architecture):

| Слой       | Путь                                             | Формат       | Retention              |
| ---------- | ------------------------------------------------ | ------------ | ---------------------- |
| **Bronze** | `data/output/bronze/{provider}/{entity}/{date}/` | JSONL + zstd | 90 дней                |
| **Silver** | `data/output/silver/{provider}/{entity}/`        | Delta Lake   | Permanent              |
| **Gold**   | `data/output/gold/{provider}/{entity}/`          | Delta Lake   | Permanent (if enabled) |

### Структура директорий

```
data/
└── output/
    ├── bronze/
    │   └── chembl/activity/2026-01-26/
    │       └── batch-001.jsonl.zst
    ├── silver/
    │   └── chembl/activity/
    │       └── _delta_log/
    ├── gold/
    │   └── chembl/activity/
    │       └── _delta_log/
    ├── checkpoints/
    │   └── chembl_activity.json
    └── quarantine/
        └── _delta_log/
```

### Экспорт данных

```bash
# Список доступных таблиц
bioetl export --list

# Экспорт в CSV
bioetl export chembl.activity

# Экспорт в Excel
bioetl export chembl.activity --format xlsx

# Экспорт Gold слоя
bioetl export chembl.activity --layer gold
```

Каждый успешный export пишет рядом с файлом данных три sidecar JSON-файла:
`*.provenance-manifest.json`, `*.licensing-manifest.json` и
`*.checksums-manifest.json`. Они фиксируют dataset bundle ID, provider
attribution/licensing metadata, sha256 checksums и явное разделение MIT-лицензии
кода от лицензий выгруженных данных.

______________________________________________________________________

## Maintenance операции

### VACUUM (очистка старых версий)

```bash
# VACUUM одной таблицы
bioetl maintenance vacuum chembl.activity

# VACUUM всех таблиц
bioetl maintenance vacuum-all

# С кастомным retention
bioetl maintenance vacuum-all --retention-days 30

# Предпросмотр
bioetl maintenance vacuum-all --dry-run
```

### Bronze Cleanup

Удаление старых Bronze файлов (по умолчанию >90 дней):

```bash
bioetl maintenance bronze-cleanup
bioetl maintenance bronze-cleanup --retention-days 60 --dry-run
```

______________________________________________________________________

## Карантин (Quarantine)

Записи, не прошедшие валидацию, помещаются в карантин для анализа.
Silver filter rejects используют тот же unified quarantine table, но обычно
разбираются отдельно от DQ validation failures.

### Просмотр карантина

```bash
# Статистика
bioetl quarantine stats --pipeline chembl_activity

# Просмотр записей
bioetl quarantine inspect --pipeline chembl_activity --limit 50

# Фильтрация по коду ошибки
bioetl quarantine inspect --pipeline chembl_activity --error-code DQ-MISSING-FIELD

# Только Silver structural rejects
bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER
bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by reason-code-field
bioetl quarantine inspect --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --limit 20

# Один конкретный run со справедливым Bronze denominator
bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --run-id <run-id>
bioetl quarantine inspect --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --run-id <run-id> --limit 20
```

`bioetl quarantine stats --error-code FILTERED_OUT_SILVER` показывает:

- общее количество Silver rejects в quarantine;
- breakdown по `reason_code`;
- breakdown по `field`;
- breakdown по `rule_type`;
- breakdown по `operator`.

Если указан `--run-id`, CLI также пытается показать `Silver Rejects vs Bronze`
на основе control-plane ledger `records_bronze` для этого запуска.
Без `--run-id` этот ratio намеренно не показывается, потому что quarantine
обычно агрегирует записи across runs.

Для focused operator grouping можно использовать:

- `bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by reason-code`
- `bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by field`
- `bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by rule-type`
- `bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by operator`
- `bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by reason-code-field`
- `bioetl quarantine stats --pipeline chembl_activity --error-code FILTERED_OUT_SILVER --group-by reason-signature`

`reason-signature` строится только из structured fields
`reason_code | rule_type | field | operator`.
Текст `Reason` / `message` удобен для чтения, но не считается stable analytics key.

`bioetl quarantine inspect --error-code FILTERED_OUT_SILVER` показывает для каждой записи:

- `payload_hash`, `dq_status`, `ingestion_ts`;
- human-readable `Reason`;
- structured fields `reason_code`, `rule_type`, `field`, `operator`,
  `expected`, `actual`;
- исходный `payload`.

### Grafana и Silver filter rejects

Для быстрого operator triage используйте shipped dashboards:

- `bioetl-overview-v2` и `bioetl-runtime` для общего объёма и динамики
  `filtered_out`;
- `bioetl-dq-v2` для DQ/quarantine summary по выбранному `$pipeline` и
  `$run_type`.

Рекомендуемый workflow:

1. Сначала проверить summary и trend в Grafana.
1. Затем перейти к `bioetl quarantine stats --error-code FILTERED_OUT_SILVER`.
1. Если нужна причина конкретной записи, использовать
   `bioetl quarantine inspect --error-code FILTERED_OUT_SILVER`.

### Повторная обработка

```bash
bioetl quarantine replay --pipeline chembl_activity --dry-run
bioetl quarantine replay --pipeline chembl_activity --max-age-days 7
```

### Очистка карантина

```bash
bioetl quarantine purge --pipeline chembl_activity --older-than-days 30 --dry-run
```

______________________________________________________________________

## Распространённые проблемы

| Проблема                | Решение                                                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| Lock acquisition failed | Дождитесь завершения активного процесса или остановите зависший локальный процесс и перезапустите пайплайн |
| Rate limit (429)        | Автоматический retry с backoff                                                                             |
| Schema drift detected   | Проверьте логи, review новых полей                                                                         |
| Checkpoint not found    | Запустите без `--resume`                                                                                   |
| DQ threshold exceeded   | Проверьте `quarantine stats`, исправьте источник                                                           |
| Circuit breaker open    | Подождите recovery (5 мин) или проверьте health провайдера                                                 |

______________________________________________________________________

## Запуск нескольких пайплайнов

### Все пайплайны провайдера

```bash
# Список пайплайнов
bioetl run-all --source chembl --list-only

# Запуск всех
bioetl run-all --source chembl

# С ограничением
bioetl run-all --source chembl --limit 100
```

### Композитные пайплайны

Для сущностей с обогащением из нескольких источников (например, publications):

```bash
bioetl run-composite --composite publication
bioetl run-composite --composite publication --seed-limit 100
bioetl run-composite --composite publication --use-cached-bronze
```

Composite execution is outside the strict exact-replay boundary. Cached Bronze
may be used as rebuild/resume evidence for every seed, dependency, and enricher
participant, but it does not make the composite run exact-replayable. Strict
exact replay remains limited to snapshot-backed source runs. The covered runtime
validation is:

```bash
uv run pytest tests/integration/ci/test_reproducibility_contract_suite.py::test_reproducibility_contract_composite_full_snapshot_envelope_rebuild_resume_matrix -q --tb=short
```

The validation records two composite control-plane occurrences and proves that
`execution_fingerprint`, effective-config semantic identity, and all participant
snapshot IDs remain stable while `run_id` and `manifest_id` differ, with
`replay_capability=resume_only` rather than `exact_replay_supported`.

______________________________________________________________________

## См. также

- [CLI Reference](../04-reference/cli.md) — полная документация CLI
- [Pipeline Configuration](pipeline-configuration.md) — настройка конфигураций
- [Metrics & Monitoring](metrics-monitoring.md) — метрики и мониторинг
- [Troubleshooting](troubleshooting.md) — решение проблем
- [Getting Started](getting-started.md) — начало работы
