______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-03'

______________________________________________________________________

# CLI Commands Cheatsheet

Краткий справочник по командам BioETL CLI для быстрого поиска.

**Версия:** 1.1.0
**Дата обновления:** 2026-09-03 (#10045)

**Оглавление:**
- [Core Make / setup](#core-make-setup) — install, test, lint, architecture
- [BioETL Application CLI](#bioetl-application-cli) — команды запуска пайплайнов
- [Unified script entry points](#unified-script-entry-points) — `python -m scripts.*`
- [OS-specific wrappers](#os-specific-wrappers) — Windows / WSL helpers
- [Memory workflow](#memory-workflow) — pre-task / post-task
- [Build & Test CLI](#build-test-cli) — команды сборки и тестирования
- [См. также](#see-also)

______________________________________________________________________

## BioETL Application CLI

### Запуск CLI

```bash
# Рекомендуемый способ (после установки)
bioetl <command> [options]

# Во время разработки с uv
uv run python -m bioetl <command> [options]

# Через активированное virtualenv
python -m bioetl <command> [options]

# Справка по команде
bioetl --help
bioetl <command> --help
```

### Основные команды запуска

### `workflow` — Декларативные workflow DAG

```bash
# Запуск workflow
bioetl workflow run <NAME> [OPTIONS]

# Статус workflow
bioetl workflow status <NAME> [OPTIONS]
```

**Ключевые опции `workflow run`:**
- `--dry-run` — предпросмотр без выполнения
- `--only-steps a,b` — выполнить только указанные шаги
- `--run-type` — тип запуска (`incremental`, `backfill`, `rebuild`)
- `--limit` — ограничение записей
- `--resume-last` — возобновить последний failed/incomplete run
- `--resume-manifest-id <ID>` — возобновить по manifest_id
- `--resume-run-id <ID>` — возобновить по run_id
- `--incremental` — продвинуть start_offset от последнего успешного запуска
- `--use-cached-bronze` — использовать Bronze cache
- `--exact-replay` — strict exact replay
- `--debug-export` — включить debug audit pack

**Примеры:**
```bash
bioetl workflow run chembl_activity --dry-run
bioetl workflow run chembl_activity --limit 1000
bioetl workflow run chembl_activity --resume-last
bioetl workflow status chembl_activity
```

### `run` — Запуск одного пайплайна

```bash
bioetl run --pipeline <NAME> [OPTIONS]
```

**Ключевые опции:**
- `--run-type` — `incremental`, `backfill`, `rebuild`
- `--limit` — максимальное количество записей
- `--resume` — продолжить с последнего checkpoint
- `--resume-run-id <ID>` — продолжить с конкретного run_id
- `--resume-manifest-id <ID>` — продолжить с конкретного manifest_id
- `--start-offset` — начать incremental run с offset
- `--dry-run` — предпросмотр без записи
- `--yes` — пропустить подтверждение для rebuild/backfill
- `--input-csv <PATH>` — фильтрация по CSV
- `--filter-column <COL>` — колонка в CSV
- `--filter-field <FIELD>` — поле API
- `--use-cached-bronze` — использовать Bronze cache
- `--exact-replay` — strict exact replay (требует snapshot-backed Bronze)
- `--required-persistence-profile` — `degraded_observable` | `replay_ready` | `forensic_grade`

**Профили персистентности (control-plane):**

| Профиль | Когда использовать | Input snapshots |
| --- | --- | --- |
| `degraded_observable` | Первый local/live extract, dev smoke | **не** требуются до старта |
| `replay_ready` (default) | Run должен быть ready for exact replay | **требуются** (cached Bronze и/или parent manifest) |
| `forensic_grade` | Максимально строгий control-plane | snapshots + ledger |

Первый live-run без Bronze cache / parent run:

```bash
bioetl run --pipeline chembl_assay --limit 1000 \
  --required-persistence-profile degraded_observable
```

Strict replay:

```bash
bioetl run --pipeline chembl_activity --use-cached-bronze --exact-replay \
  --replay-of-run-id <parent_run_id>
```

**Примеры:**
```bash
bioetl run --pipeline chembl_activity
bioetl run --pipeline chembl_activity --limit 100
bioetl run --pipeline chembl_activity --run-type rebuild --yes
bioetl run --pipeline chembl_activity --resume
bioetl run --pipeline chembl_activity --use-cached-bronze --exact-replay
bioetl run --pipeline chembl_assay --limit 1000 --required-persistence-profile degraded_observable
```

### `run-all` — Запуск всех пайплайнов провайдера

```bash
bioetl run-all --source <PROVIDER> [OPTIONS]
```

**Ключевые опции:**
- `--source` — имя провайдера (chembl, pubchem, uniprot)
- `--run-type` — тип запуска
- `--limit` — лимит записей для каждого пайплайна
- `--list-only` — только показать список пайплайнов
- `--dry-run` — предпросмотр

**Примеры:**
```bash
bioetl run-all --source chembl
bioetl run-all --source chembl --list-only
bioetl run-all --source chembl --run-type rebuild --yes
```

### `run-composite` — Запуск композитных пайплайнов

```bash
bioetl run-composite --composite <NAME> [OPTIONS]
```

**Ключевые опции:**
- `--composite` — имя композитного пайплайна
- `--resume` — продолжить с checkpoint snapshot + ledger replay
- `--seed-limit` — лимит записей для seed пайплайна
- `--enrich-only` — только указанные enrichers
- `--required-only` — только обязательные enrichers
- `--use-cached-bronze` — использовать Bronze cache

**Примеры:**
```bash
bioetl run-composite --composite publication
bioetl run-composite --composite publication --seed-limit 100
bioetl run-composite --composite publication --enrich-only crossref,openalex
```

______________________________________________________________________

## Инспекция и диагностика

### `run-manifest` — Inspect control-plane manifests and ledgers

```bash
# Показать manifest и ledger
bioetl run-manifest show <run-id|manifest-id> [--format text|json|yaml]

# Показать reproducibility audit score
bioetl run-manifest score <run-id|manifest-id> [--format json|yaml|text]

# Сравнить два запуска
bioetl run-manifest diff <left> <right> [--format text|json|yaml]

# Full-universe historical replay claim
bioetl run-manifest universe-report [--external-pack path/to/archive-pack.json ...] [--write] [--require-universal-claim] [--require-durable-evidence-coverage] [--format text|json|yaml]
```

### `diagnostics` — Диагностика системы

Click group. Root flags `--metrics` / `--health` / `--since` удалены.

```bash
bioetl diagnostics guide
bioetl diagnostics health [--provider chembl] [--json]
bioetl diagnostics metrics [--json]
bioetl diagnostics contract-checks [--json]
bioetl diagnostics dossier --run-id <RUN_ID>
bioetl diagnostics dossier --manifest-id <MANIFEST_ID>
```

### `health` — Health checks

```bash
# HTTP health server
bioetl health server [--host 127.0.0.1] [--port 8000]

# Проверка провайдеров
bioetl health check [--provider chembl] [--json]
```

**Примеры:**
```bash
bioetl health check
bioetl health check --provider chembl --provider pubchem
bioetl health check --json
```

### `checkpoint` — Управление checkpoint

```bash
# Список checkpoint
bioetl checkpoint list --pipeline <NAME>

# Correlated audit + run-manifest view
bioetl checkpoint audit-run --run-id <UUID> [--limit 100] [--format text|json|yaml]

# Checkpoint state with correlated audit and manifest context
bioetl checkpoint inspect --pipeline <NAME> [--run-id <UUID>] [--audit-limit 100] [--format text|json|yaml]
```

### `lineage` — Инспекция lineage

```bash
bioetl lineage explain --run-id <RUN_ID> [--format text|json|yaml]
bioetl lineage explain --manifest-id <MANIFEST_ID> [--format text|json|yaml]
bioetl lineage trace --dataset-ref silver:chembl.activity@12 [--format text|json|yaml]
bioetl lineage show-fragment <FRAGMENT_ID> [--semantic] [--format text|json|yaml]
```

______________________________________________________________________

## Конфигурация

### `config` — Управление конфигурацией

```bash
# Показать конфигурацию пайплайна
bioetl config show <PIPELINE> [--format yaml|json]

# Валидация конфигурации
bioetl config validate <PIPELINE>

# Глобальные настройки
bioetl config show-settings [--format yaml|json]

# Список пайплайнов
bioetl config list-pipelines
```

**Примеры:**
```bash
bioetl config show chembl_activity
bioetl config show chembl_activity --format json
bioetl config validate chembl_activity
bioetl config list-pipelines
```

### `dq` — Конфигурация Data Quality

```bash
bioetl dq validate <PIPELINE> [--config-file PATH]
bioetl dq show <PIPELINE> [--format yaml|json]
bioetl dq show-effective <PIPELINE> [--override key=value] [--format yaml|json]
bioetl dq check-compatibility <ARTIFACT1> <ARTIFACT2>
```

**Примеры:**
```bash
bioetl dq validate chembl_activity
bioetl dq show chembl_activity --format json
```

### `adr` — Работа с ADR

```bash
# Список ADR
bioetl adr list [--json]

# Просмотр ADR
bioetl adr show <NUMBER> [--raw]

# Валидация ADR репозитория
bioetl adr validate [--json]
```

______________________________________________________________________

## Экспорт данных

### `export` — Экспорт данных

```bash
bioetl export [TABLE] [OPTIONS]
```

**Опции:**
- `--list` — показать все доступные таблицы
- `--preview` — показать схему и sample данных
- `--format` — `csv`, `xlsx`, `tsv` (по умолчанию `csv`)
- `--layer` — `silver`, `gold` (по умолчанию `silver`)
- `--output <PATH>` — директория для экспорта (по умолчанию `data/exports`)
- `--limit` — максимальное количество строк
- `--columns <COLS>` — колонки для экспорта (через запятую)

**Примеры:**
```bash
bioetl export --list
bioetl export chembl.activity --preview
bioetl export chembl.activity
bioetl export chembl.activity --format xlsx
bioetl export chembl.activity --limit 10000 --columns id,name,value
bioetl export chembl.activity --layer gold
```

______________________________________________________________________

## Quarantine

### `quarantine` — Управление карантином

```bash
# Просмотр записей
bioetl quarantine inspect --pipeline <NAME> [OPTIONS]

# Статистика
bioetl quarantine stats --pipeline <NAME> [--json]

# Повторная обработка
bioetl quarantine replay --pipeline <NAME> [OPTIONS]

# Удаление старых записей
bioetl quarantine purge --pipeline <NAME> [OPTIONS]

# Пометить как решённое
bioetl quarantine resolve --pipeline <NAME> --payload-hash <HASH> [--status IGNORED|REPROCESSED]
```

**Опции `inspect`:**
- `--limit` — максимум записей (по умолчанию 100)
- `--error-code` — фильтр по коду ошибки
- `--run-id` — ограничить одним run

**Опции `stats`:**
- `--json` — вывод в JSON
- `--error-code` — ограничить одним кодом ошибки
- `--run-id` — ограничить одним run
- `--group-by` — группировка (`reason-code`, `field`, `rule-type`, `operator`, `reason-code-field`, `reason-signature`)
- `--top` — лимит элементов в группировках (по умолчанию 10)

**Опции `replay`:**
- `--error-code` — фильтр по коду ошибки
- `--max-age-days` — максимальный возраст записей (по умолчанию 7)
- `--dry-run` — предпросмотр

**Опции `purge`:**
- `--older-than-days` — удалить записи старше N дней (по умолчанию 30)
- `--dry-run` — предпросмотр
- `--force` — без подтверждения

**Примеры:**
```bash
bioetl quarantine inspect --pipeline chembl_activity
bioetl quarantine inspect --pipeline chembl_activity --error-code DQ-MISSING-FIELD
bioetl quarantine stats --pipeline chembl_activity
bioetl quarantine replay --pipeline chembl_activity --error-code DQ-MISSING-FIELD
bioetl quarantine purge --pipeline chembl_activity --older-than-days 30
```

______________________________________________________________________

## Maintenance

### `maintenance` — Maintenance операции

```bash
# VACUUM одной таблицы
bioetl maintenance vacuum <TABLE> [OPTIONS]

# VACUUM всех таблиц
bioetl maintenance vacuum-all [OPTIONS]

# Архивирование таблицы
bioetl maintenance archive <TABLE> <TARGET-PATH> [--remove-source]

# Очистка Bronze
bioetl maintenance bronze-cleanup [OPTIONS]

# Предпросмотр cleanup scope
bioetl maintenance cleanup-preview --pipeline <NAME>

# Lifecycle cleanup control-plane artifacts
bioetl maintenance control-plane-lifecycle [OPTIONS]

# План миграции контракта
bioetl maintenance plan <PIPELINE> [--format text|json|yaml]
```

**Опции `vacuum`:**
- `--retention-days`, `-r` — минимальный возраст файлов (по умолчанию 7)
- `--dry-run` — предпросмотр

**Опции `vacuum-all`:**
- `--retention-days`, `-r` — минимальный возраст файлов (по умолчанию 7)
- `--dry-run` — предпросмотр
- `--layer` — `all`, `silver`, `gold` (по умолчанию `all`)

**Опции `bronze-cleanup`:**
- `--retention-days`, `-r` — удалить файлы старше N дней (по умолчанию 90)
- `--dry-run` — предпросмотр

**Опции `control-plane-lifecycle`:**
- `--retention-days`, `-r` — удалить unprotected artifacts старше N дней (по умолчанию 90)
- `--apply` — применить план удаления
- `--format` — `text`, `json` (по умолчанию `text`)
- `--protected-manifest-id` — manifest ID для защиты
- `--protected-run-id` — run ID для защиты
- `--protected-effective-config-artifact-id` — effective-config artifact ID для защиты
- `--protected-lineage-fragment-id` — lineage fragment ID для защиты
- `--protected-snapshot-id` — snapshot ID для защиты

**Примеры:**
```bash
bioetl maintenance vacuum chembl.activity
bioetl maintenance vacuum chembl.activity --dry-run
bioetl maintenance vacuum-all --layer silver
bioetl maintenance bronze-cleanup --retention-days 90
bioetl maintenance cleanup-preview --pipeline chembl_activity
bioetl maintenance control-plane-lifecycle --retention-days 90 --apply
bioetl maintenance plan chembl_activity
```

______________________________________________________________________

## Отладка

### `debug` — Отладка пайплайнов

```bash
bioetl debug --pipeline <NAME> [--breakpoints after_silver] [--mode interactive|log] [--limit 10] [--run-type incremental]
```

**Опции:**
- `--breakpoints` — comma-separated: `after_preflight`, `after_bronze`, `after_silver`, `after_gold`, `after_dq`, `on_error`, `on_quarantine`
- `--limit` — максимальное количество записей (по умолчанию 10)
- `--mode` — `interactive` или `log`
- `--run-type` — `incremental`, `backfill`, `rebuild`

**Примеры:**
```bash
bioetl debug --pipeline chembl_activity --breakpoints after_silver
bioetl debug --pipeline chembl_activity --mode log --limit 10
```

______________________________________________________________________

## Lock управление

### `lock` — Inspect and manage local runtime locks

```bash
# Освобождение блокировки
bioetl lock release --pipeline <NAME> --run-id <UUID> [--exclusive]

# Проверка статуса блокировки
bioetl lock check --pipeline <NAME> --run-id <UUID>
```

> **Внимание:** Используйте `lock release` только если уверены, что пайплайн не выполняется.

______________________________________________________________________

## Build & Test CLI

### Основные команды Makefile

```bash
# Установка зависимостей
make install

# Запуск тестов
make test                    # Запуск стабильных тестов с coverage
make test-fast               # Быстрые тесты (не slow, не benchmark, не e2e)
make test-coverage           # Тесты с coverage gate
make test-architecture       # Архитектурные тесты
make test-unit               # Unit тесты
make test-integration        # Integration тесты (не e2e, не live)
make test-ci-local           # CI-ориентированный набор тестов
make test-confidence-local   # Unit + архитектура + контракты + 85% coverage
make test-profile            # Профилирование длительности тестов
make test-deps               # Проверка тестовых зависимостей

# Линтинг
make lint                    # ruff + mypy проверки

# Локальный запуск
make run-local               # Запуск sample pipeline (PIPELINE=chembl_activity по умолчанию)

# Качество и архитектура
make qa-debt                 # Интегральный quality/debt gate
make qa-arch-fast            # Быстрые архитектурные проверки
make security-check          # Security тесты

# Cleanup
make clean                   # Предпросмотр cleanup targets
make clean-local-artifacts   # Применить local cleanup
make clean-preflight         # Release-preflight cleanup
make clean-all               # Полный cleanup

# Диаграммы
make render-diagrams         # Рендер SVG/PNG для всех диаграмм
make render-diagrams-svg     # Только SVG (быстрее)
make render-diagrams-checks  # Валидация диаграмм (PR profile)
make render-diagrams-bundles # Регенерация Markdown bundles
make render-diagrams-all     # Полный рендер + bundles
```

### Примеры использования

```bash
# Полный цикл разработки
make install && make lint && make test

# Быстрая проверка перед коммитом
make test-fast && make qa-arch-fast

# Запуск конкретного пайплайна
make run-local PIPELINE=chembl_target

# Cleanup с применением
make clean-local-artifacts --apply

# Рендер диаграмм для документации
make render-diagrams-all
```

______________________________________________________________________

## Development Scripts

### Unified Script Entry Points

```bash
# QA скрипты (scripts/engineering/qa)
python -m scripts.engineering.qa naming_check           # Проверка именования C901
python -m scripts.engineering.qa terminology_check      # Проверка терминологии
python -m scripts.engineering.qa c901_complexity_check  # Проверка сложности C901

# CI скрипты (scripts/engineering/ci)
python -m scripts.engineering.ci quality-gate            # Quality gates
python -m scripts.engineering.ci test_runner             # Test runner

# Schema скрипты (scripts/schema)
python -m scripts.schema config_validation              # Валидация конфигурации
python -m scripts.schema config_generation               # Генерация конфигурации

# Docs скрипты (scripts/docs)
python -m scripts.docs link_check                        # Проверка ссылок
python -m scripts.docs drift_check                       # Проверка drift
python -m scripts.docs docstring_check                   # Проверка docstrings

# Diagrams скрипты (scripts/diagrams)
python -m scripts.diagrams diagram_lint                  # Lint диаграмм
python -m scripts.diagrams diagram_check                 # Проверка диаграмм
python -m scripts.diagrams diagram_render                # Рендер диаграмм

# Data operations (scripts/ops/data)
python -m scripts.ops.data checksums                     # Checksums
python -m scripts.ops.data delta                         # Delta operations
python -m scripts.ops.data data_dir                      # Data directory operations

# Repo operations (scripts/engineering/repo)
python -m scripts.engineering.repo inventory             # Инвентарь репозитория
python -m scripts.engineering.repo catalog               # Каталог
python -m scripts.engineering.repo versions              # Версии
```

### OS-Specific Wrappers

#### Windows PowerShell
```powershell
# Setup
.\setup_env_windows.ps1

# Testing
.\run_pytest.ps1
.\run_mypy.ps1
```

#### WSL/Linux
```bash
# Setup
./setup_env_wsl.sh

# Testing
./run_pytest.sh
./run_mypy.sh
```

### Memory Workflow Commands

```bash
# Pre-task workflow
python -m memory.tooling.workflow pre-task

# Post-task workflow
python -m memory.tooling.workflow post-task

# Review curated
python -m memory.tooling.workflow review-curated
```

### Docker Helper Commands

```bash
# Docker checks
make docker-check              # Проверка Docker установки
make docker-compose-check      # Валидация docker-compose.yml

# Docker build
make docker-build              # Сборка BioETL image

# Docker start/stop
make docker-start              # Запуск main stack
make docker-start-full         # Запуск full helper stack
make docker-start-monitoring   # Запуск monitoring stack (opt-in)
make docker-stop               # Остановка main stack
make docker-stop-full          # Остановка full helper stack
make docker-stop-monitoring    # Остановка monitoring stack

# Docker operations
make docker-logs               # Просмотр логов (все сервисы)
make docker-logs-bioetl       # Просмотр логов BioETL
make docker-health             # Health check сервисов
make docker-clean              # Очистка контейнеров
make docker-shell-bioetl       # Shell в bioetl контейнере
```

______________________________________________________________________

## Exit Codes

| Код | Значение                    |
| --- | --------------------------- |
| 0   | Успешное выполнение         |
| 1   | Неспецифицированная ошибка  |
| 64  | Ошибка использования CLI    |
| 80  | Ошибка конфигурации пайплайна|
| 81  | Ошибка инициализации        |
| 82  | Ошибка выполнения пайплайна |
| 83  | Превышен DQ порог           |
| 84  | Ошибка блокировки           |
| 85  | Ошибка хранилища           |
| 86  | Сетевая ошибка              |
| 87  | Ошибка checkpoint           |
| 130 | Прервано (Ctrl+C)           |
| 143 | Завершено SIGTERM           |

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

## Core Make / setup

Verified against root `Makefile` (2026-07-28). Prefer `make` targets for CI-parity local work.

| Command | Use when |
| --- | --- |
| `make install` | Create/sync project env (`uv`/deps) |
| `make test-deps` | Install test-only dependencies |
| `make lint` | Ruff + project lint surface |
| `make test` | Default test suite |
| `make test-fast` | Faster local subset |
| `make test-architecture` | Architecture / layer / inventory gates |
| `make test-unit` | Unit tests only |
| `make test-integration` | Integration tests |
| `make run-local` | Local pipeline smoke entry |
| `make qa-arch-fast` | Fast architecture QA lane |
| `make qa-debt` | Debt/governance QA lane |
| `make render-diagrams` | Render Mermaid diagram baselines |
| `make clean` / `make clean-local-artifacts` | Local hygiene |

Common pytest (when not using make):

```bash
# From repo root with venv or uv
pytest tests/unit -q
pytest tests/architecture -q --tb=line
uv run ruff check src tests
uv run mypy src
```

See also: [testing.md](../testing.md), [docs-verification.md](../docs-verification.md).

______________________________________________________________________

## Unified script entry points

Prefer `python -m scripts.<domain> ...` (or `uv run python -m ...`) over ad-hoc paths.

| Module | Purpose | Examples |
| --- | --- | --- |
| `scripts.engineering.qa` | Quality inventories, debt gates, architecture scorecards, hotspot baselines | `python -m scripts.engineering.qa report-debt-governance-gates` |
| `scripts.engineering.ci` | CI-oriented runners / quality orchestration | See `scripts/engineering/ci/` |
| `scripts.engineering.repo` | Inventory, catalog, version/root hygiene checks | `python -m scripts.engineering.repo.check_scripts_inventory` (via package entry) |
| `scripts.schema` | Config/schema generation and validation helpers | Schema parity / generation modules under `scripts/schema/` |
| `scripts.docs` | Docs links, drift, cleanup inventory | `python -m scripts.docs generate-cleanup-inventory --check` |
| `scripts.diagrams` | Diagram lint / render / quality gates | `python -m scripts.diagrams lint` |
| `scripts.ops` | Ops helpers (docker setup, data maintenance) | `scripts/ops/docker-setup.ps1` / `.sh` |
| `scripts.data_quality` / related | DQ tooling surfaces | Prefer `bioetl dq ...` for operator flows |

Architecture / quality refresh (post-change):

```bash
python -m scripts.engineering.qa.refresh_governance_artifacts
python -m scripts.diagrams lint
python -m scripts.docs check-links --links  # when available in your checkout
```

Normative policy: [RULES.md](../../00-project/RULES.md), [AGENTS.md](../../../AGENTS.md).

______________________________________________________________________

## OS-specific wrappers

### Windows (PowerShell)

| Script / pattern | Use |
| --- | --- |
| `scripts/ops/docker-setup.ps1` | Docker stack helpers (when Docker work is explicitly required) |
| `scripts/diagrams/render.ps1` | Diagram render helper |
| Project venv | `.venv-win\Scripts\python.exe -m pytest ...` |
| `uv run ...` | Preferred cross-platform runner when `uv` is installed |

### WSL / Linux

| Script / pattern | Use |
| --- | --- |
| `scripts/ops/docker-setup.sh` | Docker helpers |
| `scripts/diagrams` make targets | `make render-diagrams` |
| Codex/WSL setup | [development/codex-wsl2-setup.md](../development/codex-wsl2-setup.md) |

Default product posture remains **local-only** (ADR-010): do not require Docker/Redis for core ETL.

______________________________________________________________________

## Memory workflow

Canonical workflow: `src/memory/DAILY_WORKFLOW.md`.

```bash
# Before implementation / audit
python -m memory.tooling.workflow pre-task \
  --task-id <id> \
  --title "Short task title"

# After implementation
python -m memory.tooling.workflow post-task \
  --task-id <id>

# Cadence: review curated memory notes
python -m memory.tooling.workflow review-curated
```

Memory notes never outrank runtime code, configs, accepted ADRs, or runbooks ([AGENTS.md](../../../AGENTS.md)).

______________________________________________________________________

## См. также { #see-also }

- [CLI Reference](../../04-reference/cli.md) — полная документация по CLI
- [Running Pipelines](../running-pipelines.md) — руководство по запуску
- [Pipeline Configuration Cheatsheet](pipeline-config.md) — config hierarchy
- [Pipeline Configuration](../pipeline-configuration.md) — настройка конфигураций
- [Metrics & Monitoring](../metrics-monitoring.md) — метрики и мониторинг
- [Troubleshooting](../troubleshooting.md) — решение проблем
- [Common errors](../../05-operations/troubleshooting/common-errors.md) — error patterns
