______________________________________________________________________

Version: 6.1.3
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-08'

______________________________________________________________________

# CLI Reference

BioETL command-line interface (CLI) - основной способ взаимодействия с системой.
Построен на фреймворке **Click** для стабильности и расширяемости.

**Версия:** 6.1.2
**Дата обновления:** 2026-05-08
**Статус покрытия:** published command and operator surface

______________________________________________________________________

## Запуск CLI

```bash
# Рекомендуемый способ (после установки)
bioetl <command> [options]

# Во время разработки с uv
uv run python -m bioetl <command> [options]

# Или через активированное virtualenv
python -m bioetl <command> [options]
```

Для справки по любой команде добавьте `--help`:

```bash
bioetl --help
bioetl run --help
```

______________________________________________________________________

## Команды

### `workflow` — Декларативные workflow DAG

Bounded Phase1 surface для workflow YAML из `configs/workflows/`.

**Синтаксис:**

```bash
bioetl workflow run <NAME> [OPTIONS]
bioetl workflow status <NAME> [OPTIONS]
```

**Подкоманды:**

| Подкоманда | Назначение |
| --- | --- |
| `run` | Последовательно выполняет declarative workflow через workflow manifest / ledger / execution-state control plane |
| `status` | Показывает durable workflow status when persisted state exists, otherwise falls back to bounded topology |

**`workflow run` опции:**

| Опция | Описание |
| --- | --- |
| `--dry-run` | Включить dry-run для pipeline steps |
| `--only-steps a,b` | Выполнить только указанные шаги и их обязательные зависимости |
| `--run-type` | Override для `incremental`, `backfill`, `rebuild` |
| `--start-offset` | Override для `start_offset` у pipeline steps |
| `--limit` | Override для `limit` у pipeline steps |
| `--input-csv` | Override для CSV filter input у pipeline steps |
| `--filter-column` | Override для CSV filter column у pipeline steps |
| `--filter-field` | Override для source filter field у pipeline steps |
| `--vacuum-after-run` | Override VACUUM execution for pipeline steps |
| `--vacuum-retention-days` | Override VACUUM retention for pipeline steps |
| `--log-level` | Override log level for pipeline steps |
| `--ignore-yaml-filter` | Игнорировать YAML filter defaults у pipeline steps |
| `--skip-gold` | Пропустить Gold writes у pipeline steps |
| `--execution-context` | Override execution context у pipeline steps |
| `--use-cached-bronze/--no-cached-bronze` | Override Bronze cache usage у pipeline steps |
| `--cached-bronze-path` | Явный Bronze cache path у pipeline steps |
| `--cached-bronze-date` | Bronze cache date filter у pipeline steps |
| `--exact-replay/--no-exact-replay` | Override strict exact replay request у pipeline steps |
| `--required-persistence-profile <profile>` | Per-run override for the control-plane persistence profile (`degraded_observable`, `replay_ready`, `forensic_grade`) |
| `--replay-of-run-id` | Explicit parent `run_id` for exact replay pipeline steps |
| `--replay-of-manifest-id` | Explicit parent `manifest_id` for exact replay pipeline steps |
| `--tracing/--no-tracing` | Override distributed tracing for pipeline steps |
| `--resume-last` | Возобновить последний `failed` или `incomplete` workflow run с тем же execution fingerprint |
| `--force-steps a,b` | Явно форсировать указанные шаги при resume вместо обычного skip поведения |
| `--repair-steps a,b` | Явно пометить шаги как repair path для destructive ambiguity recovery |

**`workflow status` опции:**

| Опция | Описание |
| --- | --- |
| `--only-steps a,b` | Показать только указанные шаги и их обязательные зависимости |
| `--format text|json|yaml` | Формат вывода |
| `--run-id` | Показать persisted status для конкретного `workflow_run_id` |

**Published поведение:**

- `workflow run` создаёт immutable workflow manifest до начала исполнения.
- `workflow run` пишет append-only workflow ledger events and mutable
  workflow execution state.
- `workflow status` использует persisted workflow state, если он существует;
  если нет, команда честно возвращает bounded topology-only surface.
- `workflow run --tracing` нужен, если оператор ожидает непустой handoff в
  `Explore Traces`; без него runtime может использовать `NoOpTracing`.
- `Explore Logs` для workflow runs опирается на CLI structured logs в
  `reports/logs/bioetl.log`, которые должен ingest-ить optional `tracing`
  profile через `promtail`.
- `workflow run` starts the local metrics HTTP server on demand and performs a
  best-effort metrics publication flush on command completion so shipped
  Prometheus/Grafana workflow surfaces can observe completed workflow runs.
- workflow telemetry is published with per-run grouping identity so selected-range
  workflow dashboard panels can retain completed short-lived workflow evidence
  after the CLI process exits.
- `workflow run` now accepts the same non-conflicting pipeline runtime
  overrides as `bioetl run`, such as `--limit`, CSV/filter options,
  cache/replay options, vacuum overrides, tracing overrides, and
  `--required-persistence-profile`.
- `--required-persistence-profile degraded_observable` is still available for
  local diagnostic launches outside the replay-capable executable boundary, but
  strict workflow steps do not accept it as a remediation path for missing
  snapshot-backed Bronze evidence. Supported replay-capable launches promote
  the effective profile back to the strict published family default or fail
  closed, and cannot be used to bypass exact-replay guardrails.
- pipeline-level `--resume` is intentionally not exposed on `workflow run`;
  workflow control-plane resume stays on `--resume-last`.
- `--resume-last` использует semantic `execution_fingerprint`, а не только имя workflow.
- destructive ambiguity recovery не делает silent replay: при `repair_required`
  оператор должен использовать `--repair-steps` или `--force-steps`.

**Примеры:**

```bash
bioetl workflow run chembl_activity --dry-run
bioetl workflow run chembl_activity --limit 1000
bioetl workflow run chembl_activity --input-csv data/filter-ids.csv --filter-column molecule_id --filter-field molecule_chembl_id
bioetl workflow run chembl_activity --use-cached-bronze --exact-replay --replay-of-run-id parent-run-1 --replay-of-manifest-id manifest-parent-1
bioetl workflow status chembl_activity
bioetl workflow run publication_provider_pack --dry-run
bioetl workflow run chembl_core --dry-run
bioetl workflow run chembl_core --only-steps summarize_core_extracts
bioetl workflow run chembl_core --resume-last
bioetl workflow run chembl_core --resume-last --repair-steps reconcile_assay_target_orphans
bioetl workflow status chembl_core
bioetl workflow status chembl_core --run-id 00000000-0000-0000-0000-000000000111
bioetl workflow status chembl_core --format json
```

`workflow run`, `run`, `run-all` и `run-composite` по умолчанию также
используют `--ensure-observability-backend`, то есть пытаются автоматически
запустить detached `bioetl quarantine serve --host 0.0.0.0 --port 8081` для
Grafana `ID`/detail panels. Для отключения используйте
`--no-ensure-observability-backend`.

______________________________________________________________________

### `run` — Запуск одного пайплайна

Выполняет ETL-пайплайн для указанной сущности.

**Синтаксис:**

```bash
bioetl run --pipeline <NAME> [OPTIONS]
```

**Обязательные параметры:**

| Параметр            | Описание                                                 |
| ------------------- | -------------------------------------------------------- |
| `--pipeline <NAME>` | Имя пайплайна (соответствует YAML в `configs/entities/`) |

**Опции:**

| Опция                                    | Тип    | По умолчанию  | Описание                                                                                  |
| ---------------------------------------- | ------ | ------------- | ----------------------------------------------------------------------------------------- |
| `--run-type`                             | choice | `incremental` | Тип запуска: `incremental`, `backfill`, `rebuild`                                         |
| `--limit`                                | int    | None          | Максимальное количество записей                                                           |
| `--resume`                               | flag   | False         | Продолжить с последнего checkpoint                                                        |
| `--resume-run-id`                        | str    | None          | Возобновить ordinary pipeline из checkpoint конкретного `run_id` вместо mutable latest pointer |
| `--resume-manifest-id`                   | str    | None          | Возобновить ordinary pipeline из checkpoint конкретного `manifest_id` вместо mutable latest pointer |
| `--start-offset`                         | int    | None          | Начать incremental run с указанного offset                                                |
| `--dry-run`                              | flag   | False         | Предпросмотр без записи данных                                                            |
| `--yes`, `-y`                            | flag   | False         | Пропустить подтверждение для rebuild/backfill                                             |
| `--input-csv`                            | path   | None          | Путь к CSV с ID для фильтрации                                                            |
| `--filter-column`                        | str    | None          | Имя колонки в CSV; runtime fallback обычно `id`                                           |
| `--filter-field`                         | str    | None          | Поле API; effective default зависит от pipeline                                           |
| `--vacuum-after-run`                     | flag   | None          | Запустить VACUUM после успешного выполнения                                               |
| `--vacuum-retention-days`                | int    | None          | Retention для VACUUM (дней, override YAML config)                                         |
| `--debug`                                | flag   | False         | Включить DEBUG логирование                                                                |
| `--checkpoint-compatibility`             | choice | None          | Политика совместимости checkpoint (`observe`, `soft_fail`, `hard_fail`) |
| `--health-server/--no-health-server`     | flag   | True          | Включить HTTP health server                                                               |
| `--health-port`                          | int    | 8081          | Порт для health server                                                                    |
| `--use-cached-bronze/--no-cached-bronze` | flag   | False         | Читать Bronze cache вместо API                                                            |
| `--cached-bronze-date`                   | str    | None          | Фильтровать Bronze cache по дате `YYYY-MM-DD`                                             |
| `--cached-bronze-path`                   | path   | None          | Явный путь к каталогу Bronze cache                                                        |
| `--exact-replay/--no-exact-replay`       | flag   | False         | Включить strict exact replay внутри опубликованной support boundary с fail-closed policy  |
| `--required-persistence-profile`         | choice | None          | Per-run override для control-plane persistence profile (`degraded_observable`, `replay_ready`, `forensic_grade`) |
| `--replay-of-run-id`                     | str    | None          | Явный parent `run_id` для exact replay                                                    |
| `--replay-of-manifest-id`                | str    | None          | Явный parent `manifest_id` для exact replay                                               |

**Примеры:**

```bash
# Инкрементальный запуск (по умолчанию)
bioetl run --pipeline chembl_activity

# Запуск с политикой совместимости checkpoint
bioetl run --pipeline chembl_activity --checkpoint-compatibility observe

# С ограничением записей (для тестирования)
bioetl run --pipeline chembl_activity --limit 100

# Полная перезагрузка данных
bioetl run --pipeline chembl_activity --run-type rebuild --yes

# Предпросмотр очистки без выполнения
bioetl run --pipeline chembl_activity --run-type rebuild --dry-run

# Продолжить прерванный запуск
bioetl run --pipeline chembl_activity --resume

# Продолжить конкретный historical occurrence по run identity
bioetl run --pipeline chembl_activity --resume-run-id 7f26d7b2-2c25-4aef-bf4c-030e4f8a4f87

# Продолжить конкретный historical occurrence по manifest identity
bioetl run --pipeline chembl_activity --resume-manifest-id manifest-parent-001

# Начать incremental run с известного offset
bioetl run --pipeline chembl_activity --start-offset 5000

# С фильтрацией по CSV
bioetl run --pipeline chembl_activity \
    --input-csv data/filter-ids.csv \
    --filter-column molecule_id \
    --filter-field molecule_chembl_id

# С DEBUG логированием
bioetl run --pipeline chembl_activity --debug

# Запуск из локального Bronze cache
bioetl run --pipeline chembl_activity --use-cached-bronze

# Локальный diagnostic live/backfill запуск без replay_ready evidence claim
bioetl run --pipeline chembl_publication --limit 1000 --required-persistence-profile degraded_observable

# Strict exact replay с явным ancestry
bioetl run --pipeline chembl_activity \
    --use-cached-bronze \
    --exact-replay \
    --replay-of-run-id 7f26d7b2-2c25-4aef-bf4c-030e4f8a4f87 \
    --replay-of-manifest-id manifest-parent-001
```

**Operator distinction:**

| Surface                                              | What operators should read it as                                                                             | What operators must not read it as          |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| `--resume`                                           | Checkpoint continuation of the current pipeline execution                                                    | Strict exact replay of a prior run          |
| `--resume-run-id` / `--resume-manifest-id`           | Occurrence-pinned checkpoint continuation for one explicit historical ordinary-pipeline run                  | A request to ignore compatibility anchors   |
| `--run-type rebuild`                                 | Fresh recomputation of downstream data from available sources/Bronze                                         | Checkpoint continuation or replay proof     |
| `--exact-replay`                                     | Fail-closed request for strict exact replay on snapshot-backed inputs внутри опубликованной support boundary | Ordinary rerun, rebuild, or degraded resume |
| `replay_mode=same_data_state_recovery` in inspection | A manifested run that can recover the same data state from immutable inputs                                  | A separate CLI mode                         |
| `replay_mode=rebuild` in inspection                  | Ordinary rebuild/rerun path outside strict exact replay                                                      | Snapshot-backed same-data-state recovery    |

**Checkpoint resume policy (runtime setting):**

- `settings.pipeline.control_plane.checkpoint_compatibility_policy=observe`
  Degraded operator mode: продолжить можно только при несовместимостях вне
  canonical execution identity; identity mismatch всё равно блокирует resume.
- `settings.pipeline.control_plane.checkpoint_compatibility_policy=soft_fail`
  (по умолчанию) Заблокировать resume при несовместимости.
- `settings.pipeline.control_plane.checkpoint_compatibility_policy=hard_fail`
  Прервать запуск ошибкой при несовместимости.
- `required_persistence_profile=replay_ready` и `forensic_grade` не
  используют effective `observe`; runtime повышает policy до `hard_fail`.
- если текущий запуск выполняется как `exact_replay`, runtime принудительно
  применяет `hard_fail`, даже если в settings запрошен более мягкий policy;
  для published contract это режим strict `exact replay`, а не degraded resume.
- `--replay-of-run-id` и `--replay-of-manifest-id` допустимы только вместе с
  `--exact-replay`; они публикуют explicit replay ancestry в manifest/inspection
  surface и не должны использоваться для обычного rerun/rebuild.

Supported resume modes:

- ordinary `bioetl run --resume` uses the latest checkpoint pointer plus
  compatibility checks without ledger suffix replay;
- ordinary `bioetl run --resume-run-id` / `--resume-manifest-id` pins resume to
  one explicit historical checkpoint occurrence and still applies the same
  compatibility gates;
- composite resume uses checkpoint snapshot state as the base and then replays
  the ledger suffix strictly after `last_event_id`.
- `execution_fingerprint` остаётся canonical semantic identity, а
  `composite_run_identity` используется как occurrence-scoped resume anchor для
  composite path.
- `run_id` остаётся canonical occurrence anchor, а `manifest_id` — immutable
  persisted manifest record key для этого occurrence.

Checkpoint load telemetry uses bounded statuses. In particular:

- `observe_blocked_identity` means `observe` mode still rejected resume because
  canonical execution identity mismatched.
- `observe_loaded_degraded` means `observe` mode allowed resume only after a
  non-identity compatibility warning.

**Типы запуска:**

| Тип           | Описание                                        | Очистка данных |
| ------------- | ----------------------------------------------- | -------------- |
| `incremental` | Обработка новых записей с последнего checkpoint | Нет            |
| `backfill`    | Обработка определённого диапазона               | Silver/Gold    |
| `rebuild`     | Полная перезагрузка производных данных          | Silver/Gold    |

**Exit Codes:**

| Код | Значение                    |
| --- | --------------------------- |
| 0   | Успешное выполнение         |
| 82  | Ошибка выполнения пайплайна |
| 83  | Превышен порог Data Quality |
| 84  | Ошибка захвата блокировки   |
| 86  | Сетевая ошибка              |
| 130 | Прервано (Ctrl+C)           |

______________________________________________________________________

### `run-all` — Запуск всех пайплайнов провайдера

Последовательно выполняет все пайплайны для указанного провайдера.

**Синтаксис:**

```bash
bioetl run-all --source <PROVIDER> [OPTIONS]
```

**Опции:**

| Опция                                | Тип    | По умолчанию  | Описание                                        |
| ------------------------------------ | ------ | ------------- | ----------------------------------------------- |
| `--source`                           | str    | Required      | Имя провайдера (chembl, pubchem, uniprot и др.) |
| `--run-type`                         | choice | `incremental` | Тип запуска                                     |
| `--limit`                            | int    | None          | Лимит записей для каждого пайплайна             |
| `--dry-run`                          | flag   | False         | Показать пайплайны без выполнения               |
| `--yes`, `-y`                        | flag   | False         | Пропустить подтверждение                        |
| `--list-only`                        | flag   | False         | Только показать список пайплайнов               |
| `--debug`                            | flag   | False         | DEBUG логирование                               |
| `--health-server/--no-health-server` | flag   | True          | Включить HTTP health server                     |
| `--health-port`                      | int    | 8081          | Порт для health server                          |

**Примеры:**

```bash
# Запуск всех ChEMBL пайплайнов
bioetl run-all --source chembl

# Только просмотр списка
bioetl run-all --source chembl --list-only

# Предпросмотр
bioetl run-all --source pubchem --dry-run

# Rebuild всех пайплайнов провайдера
bioetl run-all --source chembl --run-type rebuild --yes
```

______________________________________________________________________

### `run-composite` — Запуск композитных пайплайнов

Выполняет композитный пайплайн (seed + enrichers) согласно ADR-026.

**Синтаксис:**

```bash
bioetl run-composite --composite <NAME> [OPTIONS]
```

**Опции:**

| Опция                                                          | Тип  | По умолчанию | Описание                                             |
| -------------------------------------------------------------- | ---- | ------------ | ---------------------------------------------------- |
| `--composite`                                                  | str  | Required     | Имя композитного пайплайна                           |
| `--resume`                                                     | flag | False        | Продолжить с checkpoint snapshot + ledger replay     |
| `--dry-run`                                                    | flag | False        | Предпросмотр без записи                              |
| `--seed-limit`                                                 | int  | None         | Лимит записей для seed пайплайна                     |
| `--enrich-only`                                                | str  | None         | Запустить только указанные enrichers (через запятую) |
| `--required-only`                                              | flag | False        | Пропустить опциональные enrichers                    |
| `--force-enricher`                                             | str  | None         | Принудительный перезапуск enricher                   |
| `--use-cached-bronze/--no-cached-bronze`                       | flag | False        | Читать Bronze cache вместо API                       |
| `--cached-bronze-date`                                         | str  | None         | Фильтровать Bronze cache по дате `YYYY-MM-DD`        |
| `--cached-bronze-path`                                         | path | None         | Явный путь к каталогу Bronze cache                   |
| `--cached-bronze-enrichers/--no-cached-bronze-enrichers`       | flag | None         | Override cached Bronze только для enrichers          |
| `--cached-bronze-dependencies/--no-cached-bronze-dependencies` | flag | False        | Override cached Bronze для dependency pipelines      |
| `--debug`                                                      | flag | False        | DEBUG логирование                                    |
| `--health-server/--no-health-server`                           | flag | True         | Включить HTTP health server                          |
| `--health-port`                                                | int  | 8081         | Порт для health server                               |

**Примеры:**

```bash
# Запуск композитного пайплайна публикаций
bioetl run-composite --composite publication

# С ограничением seed
bioetl run-composite --composite publication --seed-limit 100

# Только определённые enrichers
bioetl run-composite --composite publication --enrich-only crossref,openalex

# Только обязательные enrichers
bioetl run-composite --composite publication --required-only

# Composite run из Bronze cache
bioetl run-composite --composite publication --use-cached-bronze
```

Composite resume semantics:

- composite resume сначала загружает checkpoint snapshot;
- затем runtime валидирует compatibility anchors;
- среди них `composite_run_identity`, который отделён от semantic
  `execution_fingerprint` и блокирует drift между разными occurrence одного и
  того же semantic запуска;
- когда ledger attached, composite path воспроизводит suffix событий строго
  после `last_event_id`, чтобы восстановить coarse-grained lifecycle milestones
  без фабрикации rich checkpoint payloads.

______________________________________________________________________

### `run-manifest` — Inspect control-plane manifests and ledgers

Просмотр immutable run manifest и append-only ledger history для уже
запущенных пайплайнов.

Это published inspection surface и CLI-leg traceability documentation pack,
зафиксированного в
[D-01](../00-project/governance/01-documentation-governance-style-guide.md).

Поведение inspection surface зависит от rollout flags на runtime object path
`settings.pipeline.control_plane` (source-of-truth model:
`src/bioetl/infrastructure/config/_base.py`):

- `settings.pipeline.control_plane.run_manifest_enabled`
- `settings.pipeline.control_plane.run_ledger_enabled`
- `settings.pipeline.control_plane.required_persistence_profile`
- `settings.pipeline.control_plane.checkpoint_compatibility_policy`

Operational semantics:

- executable standard/composite runs требуют `run_manifest_enabled=true`; если
  новый run появился без manifest, это уже нарушение текущего runtime
  контракта, а не штатный режим;
- если `run_manifest_enabled=true` и `run_ledger_enabled=false`, `show`
  вернёт manifest payload, но без ledger history там, где такой degraded mode
  ещё допускается;
- `run_ledger_enabled=true` допустим только при `run_manifest_enabled=true`;
- `required_persistence_profile=replay_ready` требует
  `run_manifest_enabled=true` и execution context внутри опубликованной strict
  exact-replay support boundary;
- `required_persistence_profile=forensic_grade` требует и
  `run_manifest_enabled=true`, и `run_ledger_enabled=true`, плюс replay-ready /
  lineage-closure surfaces внутри той же опубликованной boundary;
- `checkpoint_compatibility_policy` принимает значения `observe`, `soft_fail`,
  `hard_fail` и управляет resume-поведением при checkpoint identity mismatch.
- `observe` не является strict reproducibility mode: canonical
  execution-identity mismatch всё равно блокирует resume, даже если другие
  degraded signals могут быть только зафиксированы warning-ом.
- strict persistence profiles (`replay_ready`, `forensic_grade`) поднимают
  effective resume policy до `hard_fail`.
- historical universe claim surfaces не должны читаться из одного `show/score`
  результата как global promise; literal wording про **любой historical run**
  требует отдельного authoritative `universe-report` artifact.

Resume contract:

- ordinary resume uses checkpoint snapshot state and compatibility checks
  without ledger suffix replay;
- composite resume uses checkpoint snapshot state as the base and then replays
  the ledger suffix strictly after `last_event_id`.

Canonical storage layout:

- `data/output/control/run_manifest/{manifest_id}.json`
- `data/output/control/run_manifest/_by_run_id/{run_id}.txt`
- `data/output/control/run_ledger/{manifest_id}.jsonl`
- `data/output/control/run_ledger/_by_run_id/{run_id}.txt`

Current event baseline for ledger-backed runs:

- `manifest_created`
- `run_started`
- `stage_started`
- `stage_completed`
- `artifact_published`
- `run_finished`
- `run_failed`
- `run_shutdown`
- `dq_policy_applied`
- `composite_dependency_completed`
- `composite_enricher_completed`
- `composite_merge_completed`
- `input_snapshot_published`

#### `run-manifest show` — Показать manifest и ledger

```bash
bioetl run-manifest show <run-id|manifest-id> [--format text|json|yaml]
```

Команда:

- сначала пытается разрешить `manifest_id` напрямую;
- затем при UUID-like identifier выполняет `run_id -> manifest_id` lookup;
- выводит `manifest`, `ledger_entries`, `diagnostics`;
- добавляет ledger history для этого же manifest, если ledger включён.
- в inspection payload сохраняет replay ancestry через
  `replay_of_run_id`, `replay_of_manifest_id`, `replay_parentage`;
- публикует semantic lineage anchors как `lineage_fragment_id`, а
  occurrence-scoped persisted lineage records как `stored_fragment_id`, когда
  historical fragment lookup должен различать несколько occurrence одного
  semantic fragment.

Когда `diagnostics` отражает rejected/degraded resume path, inspection payload
дополнительно показывает компактные forensic blocks:

- `current_identity`
- `checkpoint_identity`

Они содержат resume-critical anchors: `execution_fingerprint`, `manifest_id`,
`effective_config_hash`, `contract_ref`, `contract_version`, `exact_replay`,
`input_snapshot_ids`, `input_snapshot_content_hashes`. Для composite-specific
resume diagnostics дополнительно показывается `composite_run_identity` как
occurrence-scoped drift guard, а не как generic semantic replay identity.

Output metadata sidecars remain the operator-facing occurrence surface. Their
`runtime` block publishes `exact_replay`, `replay_of_run_id`,
`replay_of_manifest_id`, and `input_snapshot_fingerprint`; corresponding
`artifact_published` ledger details repeat these anchors together with
`execution_fingerprint`, `effective_config_artifact_id`, `contract_ref`, and
`contract_version` so replay ancestry can be checked without reconstructing the
whole manifest by hand.

В `text`/`json`/`yaml` diff output отдельное поле `replay_relationship`
показывает, является ли один manifest exact replay другого, вместо того чтобы
смешивать replay ancestry с `occurrence_only` или `semantic_drift`.

По умолчанию команда использует человекочитаемый `text`-формат. Для
machine-readable вывода укажи `--format json` или `--format yaml`.

`text`-рендерер группирует ответ по секциям `Manifest`, `Code Provenance`,
`Execution Inputs`, `Ledger`, `Diagnostics`, чтобы оператору не приходилось
читать сырой JSON при triage.

**Примеры:**

```bash
bioetl run-manifest show 7f26d7b2-2c25-4aef-bf4c-030e4f8a4f87
bioetl run-manifest show 8d166b4d-c4a8-4755-896e-cf9158c5b5ec --format yaml
bioetl run-manifest show 7f26d7b2-2c25-4aef-bf4c-030e4f8a4f87 --format json
```

#### `run-manifest score` — Показать reproducibility audit score

```bash
bioetl run-manifest score <run-id|manifest-id> [--format json|yaml|text]
```

Команда выводит только machine-readable `reproducibility_audit_score` block
из manifest diagnostics. JSON/YAML payload содержит `schema_version`,
`contract_version`, `overall_score`, `category_scores`, `blockers`,
`evidence_refs`, `scored_at` и `source`.

#### `run-manifest diff` — Сравнить два запуска

```bash
bioetl run-manifest diff <left> <right> [--format text|json|yaml]
```

Команда сравнивает все top-level поля двух manifest по каноническому JSON
сравнению значений. На практике чаще всего различаются:

- `pipeline_name`, `run_type`
- `runtime_config`, `resolved_config`
- `code_provenance`
- `source_refs`, `planned_artifacts`
- `run_id`, `manifest_id`

По умолчанию diff печатается в компактном `text`-виде. Для автоматической
обработки используй `--format json` или `--format yaml`.

Forensic/cross-surface payloads также показывают `artifact_byte_equivalence`.
Это отдельный verdict от `semantic_execution_equivalence`: semantic replay
может быть `true`, даже если sidecars или occurrence-scoped artifacts
побайтно различаются.

**Примеры:**

```bash
bioetl run-manifest diff 7f26d7b2-2c25-4aef-bf4c-030e4f8a4f87 17f6799e-6c1a-4dd6-a7a1-b1fe2ea3e9ae
bioetl run-manifest diff 8d166b4d-c4a8-4755-896e-cf9158c5b5ec d775f516-ff3e-4d66-a369-1417c3ff093f --format yaml
```

#### `run-manifest universe-report` — Full-universe historical replay claim

```bash
bioetl run-manifest universe-report [--external-pack path/to/archive-pack.json ...] [--write] [--require-universal-claim] [--require-durable-evidence-coverage] [--format text|json|yaml]
```

Команда собирает authoritative full-universe historical replay artifact из
локального retained corpus и одного или более archived/offline packs. Ключевые
режимы:

- `--write` сохраняет artifact в
  `data/output/control/historical_replay_universe/{report_id}.json`;
- `--require-universal-claim` завершает команду ошибкой, если
  `universal_claim.claimed != true`;
- `--require-durable-evidence-coverage` завершает команду ошибкой, если
  `durable_evidence_coverage_claim.claimed != true`.

Используй оба `--require-*` флага для fail-closed release/operator gates,
когда нужна строгая проверка wording уровня "любой historical run".

See also:

- [Run Manifest and Run Ledger Contract](contracts/run-manifest-ledger.md)
- [Run Manifest Inspection Runbook](../05-operations/runbooks/run-manifest-inspection.md)
- [ADR-044](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045](../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [D-01 Documentation Governance](../00-project/governance/01-documentation-governance-style-guide.md)
- [Project Navigator](../00-project/00-map.md)

______________________________________________________________________

### `adr` — Работа с ADR

Утилиты для просмотра и валидации архитектурных решений (Architecture Decision Records).

#### `adr list` — Список ADR

```bash
bioetl adr list [--json]
```

#### `adr show` — Просмотр ADR

```bash
bioetl adr show <NUMBER> [--raw]
```

#### `adr validate` — Валидация ADR репозитория

```bash
bioetl adr validate [--json]
```

______________________________________________________________________

### `export` — Экспорт данных

Экспортирует Delta-таблицы Silver/Gold в CSV, XLSX или TSV.

**Синтаксис:**

```bash
bioetl export [TABLE] [OPTIONS]
```

**Аргументы:**

| Аргумент | Описание                                                           |
| -------- | ------------------------------------------------------------------ |
| `TABLE`  | Имя таблицы в формате `provider.entity` (опционально при `--list`) |

**Опции:**

| Опция             | Тип    | По умолчанию   | Описание                             |
| ----------------- | ------ | -------------- | ------------------------------------ |
| `--list`          | flag   | False          | Показать все доступные таблицы       |
| `--preview`       | flag   | False          | Показать схему и sample данных       |
| `--format`, `-f`  | choice | `csv`          | Формат: `csv`, `xlsx`, `tsv`         |
| `--layer`, `-l`   | choice | `silver`       | Слой: `silver`, `gold`               |
| `--output`, `-o`  | path   | `data/exports` | Директория для экспорта              |
| `--limit`         | int    | None           | Максимальное количество строк        |
| `--columns`, `-c` | str    | None           | Колонки для экспорта (через запятую) |

Успешный export создает не только data-файл, но и sidecar manifests:

| Файл | Назначение |
| ---- | ---------- |
| `*.provenance-manifest.json` | Dataset bundle ID, BioETL version, source providers, schema fields, row count и data-file checksum |
| `*.licensing-manifest.json` | Provider attribution/licensing notes и отдельная запись MIT-лицензии кода |
| `*.checksums-manifest.json` | sha256/size для data-файла и sidecar manifests |

Licensing manifest не является юридическим заключением; он фиксирует known
provider obligations и не трактует merged outputs как MIT-licensed data.

**Примеры:**

```bash
# Список всех таблиц
bioetl export --list

# Предпросмотр таблицы
bioetl export chembl.activity --preview

# Экспорт в CSV (по умолчанию)
bioetl export chembl.activity

# Экспорт в Excel
bioetl export chembl.activity --format xlsx

# С ограничением строк и колонок
bioetl export chembl.activity --limit 10000 --columns id,name,value

# Экспорт Gold-слоя
bioetl export chembl.activity --layer gold

# В указанную директорию
bioetl export chembl.activity -o ./my-exports
```

______________________________________________________________________

### `debug` — Отладка пайплайнов

Запускает пайплайн с точками останова для отладки. Полезно для пошагового выполнения и инспекции промежуточных состояний.

**Синтаксис:**

```bash
bioetl debug --pipeline <NAME> [OPTIONS]
```

**Обязательные параметры:**

| Параметр            | Описание                                                 |
| ------------------- | -------------------------------------------------------- |
| `--pipeline <NAME>` | Имя пайплайна (соответствует YAML в `configs/entities/`) |

**Опции:**

| Опция                 | Тип    | По умолчанию | Описание                                                           |
| --------------------- | ------ | ------------ | ------------------------------------------------------------------ |
| `--breakpoint <STEP>` | choice | None         | Точка останова: `preflight`, `bronze`, `silver`, `gold`, `postrun` |
| `--step-into`         | flag   | False        | Пошаговое выполнение внутри этапа                                  |
| `--inspect-state`     | flag   | False        | Показать полное состояние перед каждым шагом                       |
| `--debugger-port`     | int    | 5678         | Порт для удалённого отладчика                                      |
| `--limit`             | int    | 100          | Максимальное количество записей для отладки                        |
| `--dry-run`           | flag   | True         | Не записывать данные (только чтение)                               |

**Примеры:**

```bash
# Отладка с точкой останова на этапе Silver
bioetl debug --pipeline chembl_activity --breakpoint silver

# Пошаговое выполнение с инспекцией состояния
bioetl debug --pipeline chembl_activity --step-into --inspect-state

# Отладка с удалённым отладчиком
bioetl debug --pipeline chembl_activity --debugger-port 5678
```

**См. также:**

- `bioetl run` — для обычного выполнения
- [Debugging Guide](../03-guides/troubleshooting.md)

______________________________________________________________________

### `diagnostics` — Диагностика системы

Унифицированные диагностические инструменты для операторов. Объединяет метрики, health checks, checkpoints, manifests и quarantine в единый отчёт.

**Синтаксис:**

```bash
bioetl diagnostics [OPTIONS]
```

**Опции:**

| Опция            | Тип  | По умолчанию | Описание                                        |
| ---------------- | ---- | ------------ | ----------------------------------------------- |
| `--metrics`      | flag | True         | Включить метрики производительности             |
| `--health`       | flag | True         | Включить health checks провайдеров              |
| `--checkpoints`  | flag | True         | Включить информацию о checkpoints               |
| `--manifests`    | flag | True         | Включить данные о manifests и ledgers           |
| `--quarantine`   | flag | True         | Включить статистику quarantine                  |
| `--json`         | flag | False        | Вывод в формате JSON                            |
| `--output`, `-o` | path | None         | Сохранить отчёт в файл                          |
| `--since`        | str  | `1h`         | Период для метрик (например, `1h`, `24h`, `7d`) |
| `--pipeline`     | str  | None         | Фильтр по конкретному пайплайну                 |

**Примеры:**

```bash
# Быстрая диагностика (все включено)
bioetl diagnostics

# Только метрики и health checks
bioetl diagnostics --checkpoints=false --manifests=false --quarantine=false

# Сохранить отчёт в JSON
bioetl diagnostics --json --output system-diagnostics.json

# Диагностика за последние 24 часа
bioetl diagnostics --since 24h
```

Подкоманда `bioetl diagnostics dossier` собирает one-run dossier. Она принимает
ровно один идентификатор: `--run-id <RUN_ID>` или `--manifest-id <MANIFEST_ID>`.
Manifest-rooted lookup сначала разрешает canonical `run_id` из manifest store,
затем собирает audit, checkpoint и run-manifest diagnostics. В replay/forensic
решениях учитывайте `artifact_publication_closure`: только `closed` является
полным produced-artifact evidence gate.

**См. также:**

- `bioetl health` — для health checks
- `bioetl run-manifest` — для inspection manifests

______________________________________________________________________

### `dq` — Конфигурация Data Quality

Управление конфигурацией Data Quality: валидация, просмотр и тестирование DQ правил.

**Синтаксис:**

```bash
bioetl dq [COMMAND] [OPTIONS]
```

**Команды:**

#### `dq validate` — Валидация DQ конфигурации

```bash
bioetl dq validate --entity <PROVIDER.ENTITY> [OPTIONS]
```

**Опции:**

| Опция                        | Тип  | По умолчанию | Описание                                |
| ---------------------------- | ---- | ------------ | --------------------------------------- |
| `--entity <PROVIDER.ENTITY>` | str  | None         | Сущность в формате `provider.entity`    |
| `--strict`                   | flag | False        | Strict validation (fail на warnings)    |
| `--show-rules`               | flag | False        | Показать все DQ правила                 |
| `--test-data`                | path | None         | Тестировать с пользовательскими данными |

**Примеры:**

```bash
# Валидация DQ конфигурации для сущности
bioetl dq validate --entity chembl.activity

# Показать все DQ правила
bioetl dq validate --entity chembl.activity --show-rules

# Strict validation
bioetl dq validate --entity chembl.activity --strict
```

**См. также:**

- [DQ Contracts](contracts/dq-contracts.md)
- `bioetl config validate` — для общей валидации конфигурации

______________________________________________________________________

### `lineage` — Инспекция lineage

Инструменты для анализа и визуализации lineage (происхождения данных) в пайплайнах.

**Синтаксис:**

```bash
bioetl lineage [COMMAND] [OPTIONS]
```

**Команды:**

#### `lineage show` — Показать lineage для записи

```bash
bioetl lineage show --entity <PROVIDER.ENTITY> --record-id <ID> [OPTIONS]
```

**Опции:**

| Опция                        | Тип    | По умолчанию | Описание                             |
| ---------------------------- | ------ | ------------ | ------------------------------------ |
| `--entity <PROVIDER.ENTITY>` | str    | None         | Сущность в формате `provider.entity` |
| `--record-id <ID>`           | str    | None         | Идентификатор записи                 |
| `--format`, `-f`             | choice | `text`       | Формат вывода: `text`, `json`, `dot` |
| `--depth`, `-d`              | int    | 3            | Глубина lineage графа                |
| `--include-fields`           | flag   | False        | Включить field-level lineage         |
| `--output`, `-o`             | path   | None         | Сохранить в файл                     |

**Примеры:**

```bash
# Показать lineage для записи
bioetl lineage show --entity chembl.activity --record-id ACT12345

# Вывод в формате JSON
bioetl lineage show --entity chembl.activity --record-id ACT12345 --format json

# Визуализация в формате DOT (для Graphviz)
bioetl lineage show --entity chembl.activity --record-id ACT12345 --format dot --output lineage.dot

# Полный lineage с field-level деталями
bioetl lineage show --entity chembl.activity --record-id ACT12345 --depth 5 --include-fields
```

**См. также:**

- [Lineage Architecture](contracts/run-manifest-ledger.md)
- `bioetl run --tracing` — для включения tracing

______________________________________________________________________

### `config` — Управление конфигурацией

Просмотр и валидация конфигурации пайплайнов.

#### `config show` — Показать конфигурацию пайплайна

```bash
bioetl config show <PIPELINE> [--format yaml|json]
```

**Примеры:**

```bash
bioetl config show chembl_activity
bioetl config show chembl_activity --format json
```

#### `config validate` — Валидация конфигурации

```bash
bioetl config validate <PIPELINE>
```

Выводит: Provider, Entity type, Silver table, Gold table (если есть).

#### `config show-settings` — Глобальные настройки

```bash
bioetl config show-settings [--format yaml|json]
```

Показывает все `BIOETL-*` переменные окружения (API-ключи маскируются).

#### `config list-pipelines` — Список пайплайнов

```bash
bioetl config list-pipelines
```

______________________________________________________________________

### `quarantine` — Управление карантином

CLI surface для работы с проблемными записями.

#### `quarantine inspect` — Просмотр записей

```bash
bioetl quarantine inspect --pipeline <NAME> [OPTIONS]
```

| Опция                  | Тип  | По умолчанию | Описание                                        |
| ---------------------- | ---- | ------------ | ----------------------------------------------- |
| `--pipeline`           | str  | Required     | Имя пайплайна                                   |
| `--limit`              | int  | 100          | Максимум записей                                |
| `--error-code`         | str  | None         | Фильтр по коду ошибки                           |
| `--run-id`             | str  | None         | Ограничить просмотр одним run                   |
| `--silver-filter-only` | flag | False        | Shortcut для `--error-code FILTERED_OUT_SILVER` |

**Примеры:**

```bash
bioetl quarantine inspect --pipeline chembl_activity
bioetl quarantine inspect --pipeline chembl_activity --error-code DQ-MISSING-FIELD
```

#### `quarantine stats` — Статистика

```bash
bioetl quarantine stats --pipeline <NAME> [--json]
```

| Опция                  | Тип  | По умолчанию | Описание                                                                                                               |
| ---------------------- | ---- | ------------ | ---------------------------------------------------------------------------------------------------------------------- |
| `--pipeline`           | str  | Required     | Имя пайплайна                                                                                                          |
| `--json`               | flag | False        | Вывод в JSON                                                                                                           |
| `--error-code`         | str  | None         | Ограничить статистику одним кодом ошибки                                                                               |
| `--run-id`             | str  | None         | Ограничить статистику одним run                                                                                        |
| `--silver-filter-only` | flag | False        | Shortcut для `--error-code FILTERED_OUT_SILVER`                                                                        |
| `--group-by`           | str  | None         | Фокусная Silver-группировка (`reason-code`, `field`, `rule-type`, `operator`, `reason-code-field`, `reason-signature`) |
| `--top`                | int  | 10           | Лимит элементов в группировках                                                                                         |

Показывает: общее количество, распределение по кодам ошибок, статусы (`NEW`, `IGNORED`, `REPROCESSED`).

#### `quarantine replay` — Повторная обработка

```bash
bioetl quarantine replay --pipeline <NAME> [OPTIONS]
```

| Опция            | Тип  | По умолчанию | Описание                     |
| ---------------- | ---- | ------------ | ---------------------------- |
| `--pipeline`     | str  | Required     | Имя пайплайна                |
| `--error-code`   | str  | None         | Фильтр по коду ошибки        |
| `--max-age-days` | int  | 7            | Максимальный возраст записей |
| `--dry-run`      | flag | False        | Предпросмотр                 |

`quarantine replay` подготавливает записи к повторной обработке:
в non-dry-run режиме подходящие записи помечаются как `REPROCESSED`.
Команда не запускает полный rerun пайплайна сама по себе.

#### `quarantine purge` — Удаление старых записей

```bash
bioetl quarantine purge --pipeline <NAME> [OPTIONS]
```

| Опция               | Тип  | По умолчанию | Описание                     |
| ------------------- | ---- | ------------ | ---------------------------- |
| `--older-than-days` | int  | 30           | Удалить записи старше N дней |
| `--dry-run`         | flag | False        | Предпросмотр                 |
| `--force`           | flag | False        | Без подтверждения            |

#### `quarantine resolve` — Пометить как решённое

```bash
bioetl quarantine resolve --pipeline <NAME> --payload-hash <HASH> [--status IGNORED|REPROCESSED]
```

Допустимые значения `--status`: `IGNORED`, `REPROCESSED`.

______________________________________________________________________

### `checkpoint` — Управление checkpoint

Checkpoint inspection surfaces also expose correlated run-manifest diagnostics.
For `bioetl checkpoint audit-run --run-id <UUID>`, the text renderer now
includes:

- `persistence_profile`;
- `composite_resume_reconstructability` for the bounded composite replay
  contract;
- `alert_signals`;
- `next_steps`.

CLI reference owns the command and option inventory for this inspection
surface. The control-plane contract owns persistence-profile semantics,
event taxonomy, and rollout flags.

#### `checkpoint list` — Список checkpoint

```bash
bioetl checkpoint list --pipeline <NAME>
```

| Опция        | Тип | По умолчанию | Описание      |
| ------------ | --- | ------------ | ------------- |
| `--pipeline` | str | Required     | Имя пайплайна |

#### `checkpoint audit-run` — Correlated audit + run-manifest view for one run

```bash
bioetl checkpoint audit-run --run-id <UUID> [--limit 100] [--format text|json|yaml]
```

| Опция      | Тип    | По умолчанию | Описание               |
| ---------- | ------ | ------------ | ---------------------- |
| `--run-id` | str    | Required     | `RUN_ID` запуска       |
| `--limit`  | int    | `100`        | Максимум audit entries |
| `--format` | choice | `text`       | `text`, `json`, `yaml` |

Показывает correlated inspection payload для одного `run_id`:

- audit entries;
- linked run-manifest diagnostics;
- `persistence_profile`;
- `composite_resume_reconstructability`;
- `alert_signals`;
- `next_steps`.

#### `checkpoint inspect` — Checkpoint state with correlated audit and manifest context

```bash
bioetl checkpoint inspect --pipeline <NAME> [--run-id <UUID>] [--audit-limit 100] [--format text|json|yaml]
```

| Опция           | Тип    | По умолчанию | Описание                          |
| --------------- | ------ | ------------ | --------------------------------- |
| `--pipeline`    | str    | Required     | Имя пайплайна                     |
| `--run-id`      | str    | None         | Опциональный `RUN_ID`             |
| `--audit-limit` | int    | `100`        | Максимум correlated audit entries |
| `--format`      | choice | `text`       | `text`, `json`, `yaml`            |

Показывает:

- checkpoint metadata and identity anchors;
- correlated run-manifest context;
- compatibility taxonomy;
- bounded audit history for triage.

______________________________________________________________________

### `health` — Health checks

#### `health server` — HTTP health server

```bash
bioetl health server [--host 127.0.0.1] [--port 8081]
```

Для Grafana `5. Silver Reject Explorer` используйте:

```bash
bioetl health server --host 0.0.0.0 --port 8081
```

**Endpoints:**

- `GET /health` — общий статус
- `GET /health/live` — Kubernetes liveness probe
- `GET /health/ready` — Kubernetes readiness probe
- `GET /health/providers` — детальный статус провайдеров

#### `health check` — Проверка провайдеров

```bash
bioetl health check [--provider chembl] [--json]
```

Проверяет connectivity и health всех или указанных провайдеров.

**Примеры:**

```bash
bioetl health check
bioetl health check --provider chembl --provider pubchem
bioetl health check --json
```

______________________________________________________________________

### `lock` — Inspect and manage local runtime locks

Inspection and manual release surface for the Local-Only runtime lock files.
This CLI group does **not** represent an inter-process lock manager or external
coordinator.

#### `lock release` — Освобождение блокировки

```bash
bioetl lock release --pipeline <NAME> --run-id <UUID> [--exclusive]
```

> **Внимание:** Используйте только если уверены, что пайплайн не выполняется.

#### `lock check` — Проверка статуса блокировки

```bash
bioetl lock check --pipeline <NAME> --run-id <UUID>
```

______________________________________________________________________

### `maintenance` — Maintenance операции

#### `maintenance vacuum` — VACUUM одной таблицы

```bash
bioetl maintenance vacuum <TABLE> [OPTIONS]
```

| Опция                    | Тип  | По умолчанию | Описание                   |
| ------------------------ | ---- | ------------ | -------------------------- |
| `--retention-days`, `-r` | int  | 7            | Минимальный возраст файлов |
| `--dry-run`              | flag | False        | Предпросмотр               |

**Примеры:**

```bash
bioetl maintenance vacuum chembl.activity
bioetl maintenance vacuum chembl.activity --dry-run
bioetl maintenance vacuum chembl.activity -r 30
```

#### `maintenance vacuum-all` — VACUUM всех таблиц

```bash
bioetl maintenance vacuum-all [OPTIONS]
```

| Опция                    | Тип    | По умолчанию | Описание                      |
| ------------------------ | ------ | ------------ | ----------------------------- |
| `--retention-days`, `-r` | int    | 7            | Минимальный возраст файлов    |
| `--dry-run`              | flag   | False        | Предпросмотр                  |
| `--layer`                | choice | `all`        | Слой: `all`, `silver`, `gold` |

#### `maintenance archive` — Архивирование таблицы

```bash
bioetl maintenance archive <TABLE> <TARGET-PATH> [--remove-source]
```

#### `maintenance bronze-cleanup` — Очистка Bronze

```bash
bioetl maintenance bronze-cleanup [OPTIONS]
```

| Опция                    | Тип  | По умолчанию | Описание                    |
| ------------------------ | ---- | ------------ | --------------------------- |
| `--retention-days`, `-r` | int  | 90           | Удалить файлы старше N дней |
| `--dry-run`              | flag | False        | Предпросмотр                |

#### `maintenance cleanup-preview` — Предпросмотр cleanup scope

```bash
bioetl maintenance cleanup-preview --pipeline <NAME>
```

Показывает dry-run scope для Silver/Gold cleanup по конкретному pipeline без
фактического удаления данных.

| Опция        | Тип | По умолчанию | Описание                                   |
| ------------ | --- | ------------ | ------------------------------------------ |
| `--pipeline` | str | Required     | Имя pipeline (например, `chembl_activity`) |

**Пример:**

```bash
bioetl maintenance cleanup-preview --pipeline chembl_activity
```

#### `maintenance control-plane-lifecycle` — Lifecycle cleanup control-plane artifacts

```bash
bioetl maintenance control-plane-lifecycle [OPTIONS]
```

Планирует или применяет cleanup для `data/output/control`,
`data/output/checkpoints` и `data/output/bronze`. По умолчанию команда работает
в dry-run режиме.

| Опция                                      | Тип    | По умолчанию | Описание                                    |
| ------------------------------------------ | ------ | ------------ | ------------------------------------------- |
| `--retention-days`, `-r`                   | int    | 90           | Удалить unprotected artifacts старше N дней |
| `--apply`                                  | flag   | False        | Применить план удаления                     |
| `--format`                                 | choice | `text`       | Формат вывода: `text`, `json`               |
| `--protected-manifest-id`                  | repeat | None         | Manifest ID, который нельзя удалять         |
| `--protected-run-id`                       | repeat | None         | Run ID, который нельзя удалять              |
| `--protected-effective-config-artifact-id` | repeat | None         | Effective-config artifact ID для защиты     |
| `--protected-lineage-fragment-id`          | repeat | None         | Lineage fragment ID для защиты              |
| `--protected-snapshot-id`                  | repeat | None         | Content-addressed snapshot ID для защиты    |

**Примеры:**

```bash
bioetl maintenance control-plane-lifecycle --retention-days 90
bioetl maintenance control-plane-lifecycle --retention-days 90 --apply
bioetl maintenance control-plane-lifecycle --format json
```

#### `maintenance plan` — План миграции контракта

```bash
bioetl maintenance plan <PIPELINE> [--format text|json|yaml]
```

Planner-only inspection command для versioned contract rollout. Команда не
выполняет orchestration и не запускает backfill автоматически; она печатает
transition summary, required actions и operator notes для выбранного pipeline.

| Опция      | Тип    | По умолчанию | Описание                              |
| ---------- | ------ | ------------ | ------------------------------------- |
| `--format` | choice | `text`       | Формат вывода: `text`, `json`, `yaml` |

**Примеры:**

```bash
bioetl maintenance plan chembl_activity
bioetl maintenance plan chembl_activity --format json
bioetl maintenance plan chembl_activity --format yaml
```

Типичный planner output включает:

- active contract version и rollout mode;
- read/write/shadow versions;
- migration transitions и migration guides, если они объявлены;
- required actions. Для `affects_hash=true` planner возвращает как минимум:
  `silver_backfill_rebuild`, `gold_backfill_rebuild`,
  `verification_before_cutover`.

______________________________________________________________________

## Переменные окружения

| Переменная               | Описание                       | По умолчанию |
| ------------------------ | ------------------------------ | ------------ |
| `BIOETL_ENV`             | Окружение (`dev`, `prod`)      | `dev`        |
| `BIOETL_DATA_DIR`        | Директория данных              | `./data`     |
| `BIOETL_LOG_LEVEL`       | Уровень логирования            | `INFO`       |
| `BIOETL_METRICS_ENABLED` | Включить Prometheus метрики    | `true`       |
| `BIOETL_METRICS_PORT`    | Порт для Prometheus            | `8000`       |
| `BIOETL_TRACING_ENABLED` | Включить OpenTelemetry tracing | `false`      |

**API-ключи провайдеров:**

- `BIOETL_UNIPROT_API_KEY` — optional higher-throughput UniProt profile
- `BIOETL_OPENALEX_API_KEY` — required for production-like OpenAlex runs
- `BIOETL_OPENALEX_EMAIL` — optional OpenAlex contact attribution
- `BIOETL_SEMANTICSCHOLAR_API_KEY`

______________________________________________________________________

## Exit Codes

Коды возврата следуют стандартам Unix (sysexits.h):

| Код | Константа          | Описание                              |
| --- | ------------------ | ------------------------------------- |
| 0   | OK                 | Успешное выполнение                   |
| 1   | FAIL               | Неспецифицированная ошибка            |
| 64  | EX_USAGE           | Ошибка использования командной строки |
| 65  | EX_DATAERR         | Ошибка формата данных                 |
| 66  | EX_NOINPUT         | Не удалось открыть входные данные     |
| 67  | EX_NOUSER          | Адресат неизвестен                    |
| 68  | EX_NOHOST          | Имя хоста неизвестно                  |
| 69  | EX_UNAVAILABLE     | Сервис недоступен                     |
| 70  | EX_SOFTWARE        | Внутренняя ошибка ПО                  |
| 71  | EX_OSERR           | Ошибка ОС                             |
| 72  | EX_OSFILE          | Отсутствует критический файл ОС       |
| 73  | EX_CANTCREAT       | Не удалось создать выходной файл      |
| 74  | EX_IOERR           | Ошибка ввода-вывода                   |
| 75  | EX_TEMPFAIL        | Временная ошибка                      |
| 76  | EX_PROTOCOL        | Ошибка протокола                      |
| 77  | EX_NOPERM          | Отказано в доступе                    |
| 78  | EX_CONFIG          | Ошибка конфигурации                   |
| 80  | CONFIG_ERROR       | Ошибка конфигурации пайплайна         |
| 81  | INIT_ERROR         | Ошибка инициализации                  |
| 82  | PIPELINE_ERROR     | Ошибка выполнения пайплайна           |
| 83  | DATA_QUALITY_ERROR | Превышен DQ порог                     |
| 84  | LOCK_ERROR         | Ошибка блокировки                     |
| 85  | STORAGE_ERROR      | Ошибка хранилища                      |
| 86  | NETWORK_ERROR      | Сетевая ошибка                        |
| 87  | CHECKPOINT_ERROR   | Ошибка checkpoint                     |
| 130 | SIGINT             | Прервано Ctrl+C                       |
| 143 | SIGTERM            | Завершено SIGTERM                     |

______________________________________________________________________

## См. также

- [Running Pipelines](../03-guides/running-pipelines.md) — руководство по запуску
- [Pipeline Configuration](../03-guides/pipeline-configuration.md) — настройка конфигураций
- [Metrics & Monitoring](../03-guides/metrics-monitoring.md) — метрики и мониторинг
- [Troubleshooting](../03-guides/troubleshooting.md) — решение проблем
