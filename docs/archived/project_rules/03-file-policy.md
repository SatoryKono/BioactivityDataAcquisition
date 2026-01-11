# File Policy
*Синхронизировано с RULES.md v5.10 (2026-01-06)*

Этот документ фиксирует структуру репозитория и правила размещения файлов.

## Уровни Требований (RFC 2119)
- **MUST**: Абсолютное требование.
- **SHOULD**: Сильная рекомендация.
- **MAY**: На усмотрение разработчика.

## Структура каталогов

Проект следует архитектурному паттерну Ports & Adapters (Hexagonal) + DDD.

```text
.
├── assets/                     # MkDocs theme assets (stylesheets, js)
├── benchmarks/                 # Performance tests (pytest-benchmark)
├── configs/                    # Runtime конфигурации (YAML)
│   ├── pipelines/              # Конфиги пайплайнов по провайдерам
│   │   └── {provider}/         # e.g., chembl/, pubchem/
│   │       └── {entity}.yaml   # e.g., activity.yaml
│   └── providers/              # Конфиги провайдеров (rate limits, URLs)
├── data/                       # Данные (Bronze/Silver/Gold)
│   ├── bronze/                 # {format_version}/{provider}/{entity}/{date}/
│   ├── silver/                 # Delta Lake таблицы
│   └── gold/                   # Витрины
├── docs/                       # Документация
│   ├── application/            # Use Cases (описания пайплайнов)
│   │   └── pipelines/          # По провайдерам и сущностям
│   ├── architecture/           # ADR, принципы
│   │   ├── decisions/          # NNNN-title-in-kebab-case.md
│   │   └── diagrams/           # Mermaid/PlantUML
│   ├── contracts/              # Data Contracts
│   │   └── gold/               # JSON Schema для Gold-таблиц
│   ├── domain/                 # Глоссарий, Схемы (Pandera)
│   │   └── schemas/            # Документация по схемам
│   ├── guides/                 # How-to руководства
│   ├── infrastructure/         # Адаптеры: Клиенты, Логирование
│   ├── interfaces/             # CLI документация
│   ├── templates/              # Шаблоны (pipeline-review-checklist.md)
│   └── 00-map.md               # Навигатор по проекту
├── grafana/                    # Grafana dashboards (observability)
│   ├── dashboards/             # JSON dashboard definitions
│   └── provisioning/           # Auto-provisioning configs
├── qc/                         # Quality Control artifacts
│   └── golden/                 # Golden test artifacts
├── scripts/                    # Operational scripts (не утилиты!)
│   ├── check_architecture.py   # CI архитектурные проверки
│   └── cleanup_cache.py        # Очистка кэшей
├── src/                        # Исходный код
│   ├── bioetl/                 # Root package
│   │   ├── application/        # Пайплайны, Use Cases
│   │   │   └── pipelines/      # {provider}/{entity}/
│   │   ├── composition/        # DI-контейнер, factories, bootstrap
│   │   ├── domain/             # Чистая логика, Protocols
│   │   │   ├── configs/        # Pydantic-модели конфигов
│   │   │   ├── ports/          # Интерфейсы (typing.Protocol)
│   │   │   └── schemas/        # Pandera-схемы
│   │   ├── infrastructure/     # Адаптеры
│   │   │   ├── clients/        # HTTP клиенты по провайдерам
│   │   │   └── config/         # Инфраструктурные модели
│   │   └── interfaces/         # CLI (Click)
│   └── tools/                  # Утилиты проекта
│       ├── audit_structure.py  # Аудит структуры проекта
│       └── create_pipeline.py  # Генератор boilerplate
└── tests/                      # Тесты (зеркалят src/)
    ├── architecture/           # Архитектурные тесты
    ├── benchmarks/             # Интеграция с pytest-benchmark
    ├── fixtures/               # VCR.py кассеты
    │   └── vcr/                # Записи API-ответов
    ├── integration/            # Интеграционные тесты
    └── unit/                   # Unit тесты
```

## Medallion Architecture Paths (MUST)

| Уровень | Path Pattern | Формат |
|---------|--------------|--------|
| Bronze | `bronze/{format_version}/{provider}/{entity}/{date}/` | JSONL + zstd |
| Silver | `silver/{provider}/{entity}/year={YYYY}/month={MM}/` | Delta Lake |
| Gold | `gold/{use_case}/` | Delta/Parquet |

**Bronze Lifecycle**:
- Формат (JSONL) зафиксирован в `{format_version}` (e.g., `/v1/`).
- Изменение формата **MUST** создавать новую ветку (`/v2/`).
- Миграция "in-place" **MUST NOT**.

## Политика Корневых Папок (MUST)

Создание **НОВЫХ** папок в корне репозитория **MUST NOT** без обоснования в ADR.

### Допустимые корневые каталоги

| Каталог | Назначение | Комментарий |
|---------|------------|-------------|
| `src/` | Исходный код (bioetl, tools) | **Core** |
| `tests/` | Тесты (зеркалят src/) | **Core** |
| `docs/` | Документация | **Core** |
| `configs/` | Runtime конфигурации (YAML) | **Core** |
| `data/` | Данные (Bronze/Silver/Gold) | В `.gitignore`, кроме структуры |
| `qc/` | Quality Control артефакты | |
| `scripts/` | Операционные скрипты (CI, архитектура) | Не путать с `src/tools/` |
| `benchmarks/` | Performance тесты (pytest-benchmark) | |
| `grafana/` | Grafana dashboards (observability) | |
| `assets/` | MkDocs theme assets | |
| `reports/` | Временные отчёты | Не коммитятся, в `.gitignore` |
| `.github/` | GitHub workflows | |
| `.cursor/` | Cursor IDE rules | |
| `.trae/` | Trae rules | |
| `.windsurf/` | Windsurf rules | |
| `.claude/` | Claude Code config | |
| `.codex/` | OpenAI Codex config | |
| `.jules/` | Jules config | |

### Разграничение scripts/ и src/tools/

| Директория | Назначение | Примеры |
|------------|------------|---------|
| `scripts/` | CI/операционные скрипты, запускаемые извне | `check_architecture.py`, `cleanup_cache.py` |
| `src/tools/` | Утилиты проекта, часть кодовой базы | `create_pipeline.py`, `audit_structure.py` |

**Правило**: Если скрипт импортирует `bioetl` модули → `src/tools/`. Если standalone → `scripts/`.

## Правила именования

### 1. Markdown файлы (MUST)

- `kebab-case` (например, `system-design.md`).
- Префиксы `NN-` для упорядочивания (например, `01-getting-started.md`).

### 2. ADR (MUST)

- Размещаются в `docs/architecture/decisions/`.
- Формат: `NNNN-title-in-kebab-case.md`.

### 3. Пайплайны (MUST)

| Артефакт | Path |
|----------|------|
| Документация | `docs/application/pipelines/{provider}/{entity}/` |
| Код | `src/bioetl/application/pipelines/{provider}/{entity}/` |
| Конфиг | `configs/pipelines/{provider}/{entity}.yaml` |

### 4. Data Contracts (MUST)

- Gold-схемы **MUST** публиковаться в `docs/contracts/gold/{entity}.json`.
- Версионирование: `{entity}_v{major}.{minor}`.

### 5. Конфигурации пайплайнов (MUST)

```yaml
# configs/pipelines/{provider}/{entity}.yaml
pipeline:
  name: {entity}_{provider}
  provider: {provider}
  entity: {entity}

source:
  type: api | csv | parquet
  load_strategy: incremental | full

sink:
  silver:
    path: s3://bioetl/silver/{provider}/{entity}/
    format: delta
    mode: merge
    forensic_retention: false  # true для Critical tables

dq_rules:
  soft_fail_threshold: 0.05
  hard_fail_threshold: 0.20
```

## Принципы "Docs-as-Code" (MUST)

### Источники истины

| Артефакт | Код | Документация |
|----------|-----|--------------|
| Схемы данных | `src/.../schemas/` | `docs/domain/schemas/` |
| Пайплайны | `src/.../pipelines/` | `docs/application/pipelines/` |
| Data Contracts | Pandera schemas | `docs/contracts/gold/` |

### Синхронизация (MUST)

- Изменения в `src/` **MUST** отражаться в `docs/00-map.md`.
- Breaking changes **MUST** фиксироваться в `CHANGELOG.md` и ADR.
- Автогенерируемые секции **MUST** помечаться `<!-- generated -->`.

## Environment Isolation (MUST)

| Среда | S3 Bucket | Redis DB | Доступ к Prod |
|-------|-----------|----------|---------------|
| Dev | `bioetl-dev` | db0 | Нет |
| Staging | `bioetl-staging` | db1 | Нет |
| Prod | `bioetl-prod` | db2 | Только CI Runner |

## Quarantine Path (MUST)

Unified Quarantine таблица: `common.quarantine`.
- Retention: 30 дней (S3 Lifecycle).
- Linkage **MUST** содержать ссылку на Bronze (`bronze_file_uri` или `batch_id`).

## Lineage Log (MUST)

Таблица `sys.lineage_log`:
- `_source_batch_id` → список Bronze файлов (S3 paths).
- Версия трансформации.
- Параметры запуска.

Полные пути в каждой строке данных **MUST NOT**.

## Диаграммы (SHOULD)

Соблюдать `docs/architecture/diagrams/00-diagramming-policy.md`:
- Первичный формат: Mermaid/PlantUML (текст).
- Один файл — одна диаграмма.
- Обновлять при архитектурных изменениях.
