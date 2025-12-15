# File Policy
*Синхронизировано с RULES.md v5.0 (2025-12-15)*

Этот документ фиксирует структуру репозитория и правила размещения файлов.

## Уровни Требований (RFC 2119)
- **MUST**: Абсолютное требование.
- **SHOULD**: Сильная рекомендация.
- **MAY**: На усмотрение разработчика.

## Структура каталогов

Проект следует архитектурному паттерну Ports & Adapters (Hexagonal) + DDD.

```text
.
├── configs/                    # Runtime конфигурации (YAML)
│   ├── pipelines/              # Конфиги пайплайнов по провайдерам
│   │   └── {provider}/         # e.g., chembl/, pubchem/
│   │       └── {entity}.yaml   # e.g., activity.yaml
│   └── providers/              # Конфиги провайдеров (rate limits, URLs)
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
├── src/                        # Исходный код
│   └── bioetl/                 # Root package
│       ├── application/        # Пайплайны, Use Cases
│       │   └── pipelines/      # {provider}/{entity}/
│       ├── domain/             # Чистая логика, Protocols
│       │   ├── configs/        # Pydantic-модели конфигов
│       │   ├── ports.py        # Интерфейсы (typing.Protocol)
│       │   └── schemas/        # Pandera-схемы
│       ├── infrastructure/     # Адаптеры
│       │   ├── clients/        # HTTP клиенты по провайдерам
│       │   └── config/         # Инфраструктурные модели
│       └── interfaces/         # CLI (Typer)
├── tests/                      # Тесты (зеркалят src/)
│   ├── fixtures/               # VCR.py кассеты
│   │   └── vcr/                # Записи API-ответов
│   └── golden/                 # Эталонные данные
├── data/                       # Данные (Bronze/Silver/Gold)
│   ├── bronze/                 # {format_version}/{provider}/{entity}/{date}/
│   ├── silver/                 # Delta Lake таблицы
│   └── gold/                   # Витрины
└── qc/                         # Quality Control
    └── golden/                 # Golden test artifacts
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

## Запрет корневых папок (MUST)

- Создание новых папок в корне репозитория **MUST NOT**.
- Утилиты и скрипты **MUST** размещаться в `src/tools/`.
- Допустимые корневые каталоги: `src/`, `tests/`, `docs/`, `configs/`, `data/`, `.github/`, `.cursor/`, `.trae/`, `.windsurf/`, `qc/`.
- Временные отчёты → `reports/` (не коммитятся, см. `.gitignore`).

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
