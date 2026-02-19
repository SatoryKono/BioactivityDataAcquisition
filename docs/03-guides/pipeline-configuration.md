# Pipeline Configuration Guide

Руководство по настройке конфигурации ETL-пайплайнов в BioETL.

**Версия:** 6.0.0
**Дата обновления:** 2026-02-03

----------------------------------------------------------------------

## Обзор

BioETL использует **YAML-файлы** для конфигурации пайплайнов. Все конфигурации валидируются через **Pydantic** при загрузке, обеспечивая типобезопасность и раннее обнаружение ошибок.

### Ключевые особенности

- **Convention over Configuration (ADR-029):** Пути и ссылки вычисляются автоматически
- **Иерархическое наследование:** Конфиги наследуют из `-base.yaml`
- **Иерархические DQ/Filter правила (ADR-027/028):** 3-уровневая иерархия с merge
- **Pydantic валидация:** Схемы проверяются при загрузке
- **Immutable Domain Objects:** Конфиги преобразуются в frozen dataclasses

----------------------------------------------------------------------

## Структура директорий

```
configs/
├── pipelines/                    # Конфигурации пайплайнов (26 = 21 entity + 5 composite)
│   ├── -base.yaml               # Базовая конфигурация v2.1.0 (491 строка)
│   ├── -schema.json             # JSON Schema для валидации
│   ├── chembl/                  # 14 entity configs
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   ├── assay-parameters.yaml
│   │   ├── cell-line.yaml
│   │   ├── compound-record.yaml
│   │   ├── molecule.yaml
│   │   ├── protein-class.yaml
│   │   ├── publication.yaml
│   │   ├── publication-similarity.yaml
│   │   ├── publication-term.yaml
│   │   ├── subcellular-fraction.yaml
│   │   ├── target.yaml
│   │   ├── target-component.yaml
│   │   └── tissue.yaml
│   ├── pubchem/                 # 1 entity config
│   │   └── compound.yaml
│   ├── uniprot/                 # 2 entity configs
│   │   ├── idmapping.yaml
│   │   └── protein.yaml
│   ├── pubmed/                  # 1 entity config
│   │   └── publication.yaml
│   ├── crossref/                # 1 entity config
│   │   └── publication.yaml
│   ├── openalex/                # 1 entity config
│   │   └── publication.yaml
│   ├── semanticscholar/         # 1 entity config
│   │   └── publication.yaml
│   └── composite/               # 5 composite configs (ADR-026)
│       ├── activity.yaml        # chembl-activity + enrichers
│       ├── assay.yaml           # chembl-assay + enrichers
│       ├── molecule.yaml        # chembl-molecule + enrichers
│       ├── publication.yaml     # chembl-publication + enrichers
│       └── target.yaml          # chembl-target + enrichers
├── quality/                      # Data Quality правила (ADR-027, 31 файл)
│   ├── -defaults.yaml           # Глобальные DQ defaults (soft-fail=0.05, hard-fail=0.20)
│   ├── providers/               # 7 provider-specific DQ
│   │   ├── chembl.yaml
│   │   ├── crossref.yaml
│   │   ├── openalex.yaml
│   │   ├── pubchem.yaml
│   │   ├── pubmed.yaml
│   │   ├── semanticscholar.yaml
│   │   └── uniprot.yaml
│   └── entities/                # 23 entity-specific DQ
│       ├── chembl/
│       │   ├── activity.yaml
│       │   ├── assay.yaml
│       │   └── ...              # 14 entity DQ configs
│       ├── crossref/
│       │   └── publication.yaml
│       ├── openalex/
│       │   └── publication.yaml
│       ├── pubchem/
│       │   └── compound.yaml
│       ├── pubmed/
│       │   └── publication.yaml
│       ├── semanticscholar/
│       │   └── publication.yaml
│       └── uniprot/
│           ├── idmapping.yaml
│           ├── protein.yaml
│           └── target.yaml
├── filters/                      # Фильтры данных (ADR-028, 35 файлов)
│   ├── -defaults.yaml           # batch-size: 100
│   ├── providers/               # Provider-specific batch-sizes
│   │   ├── chembl.yaml
│   │   ├── crossref.yaml
│   │   ├── openalex.yaml
│   │   ├── pubchem.yaml
│   │   ├── pubmed.yaml
│   │   ├── semanticscholar.yaml
│   │   └── uniprot.yaml
│   └── entities/                # 27 entity-specific filter configs
│       ├── chembl/
│       │   ├── activity.yaml
│       │   └── ...              # 14 entity filter configs
│       ├── composite/
│       │   ├── activity.yaml
│       │   └── ...              # 5 composite filter configs
│       └── ...                  # Other providers
└── sources/                      # Конфигурации источников (7 файлов)
    ├── chembl.yaml
    ├── crossref.yaml
    ├── openalex.yaml
    ├── pubchem.yaml
    ├── pubmed.yaml
    ├── semanticscholar.yaml
    └── uniprot.yaml
```

### Статистика конфигураций

| Категория                 | Количество | Описание                               |
| ------------------------- | ---------- | -------------------------------------- |
| Pipeline configs (entity) | 21         | Regular ETL pipelines                  |
| Composite configs         | 5          | Multi-provider pipelines (ADR-026)     |
| DQ configs (quality/)     | 31         | 1 defaults + 7 providers + 23 entities |
| Filter configs (filters/) | 35         | 1 defaults + 7 providers + 27 entities |
| Source configs            | 7          | Один на провайдера                     |
| **Итого**                 | **71**     | Все конфиги валидированы               |

----------------------------------------------------------------------

## Pipeline YAML конфиг

### Минимальный конфиг

Благодаря наследованию из `-base.yaml`, минимальный конфиг содержит только переопределения:

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline-name: chembl-activity
provider: chembl
entity-type: activity
version: "1.2.0"
business-primary-keys: ["activity-id"]
silver-table: "chembl-activity"
gold-table: "chembl-activity"
```

### Полная структура конфига

| Секция                  | Описание                           | Обязательно          |
| ----------------------- | ---------------------------------- | -------------------- |
| `pipeline-name`         | Уникальный идентификатор пайплайна | Да                   |
| `provider`              | Имя провайдера (lowercase)         | Да                   |
| `entity-type`           | Тип сущности                       | Да                   |
| `version`               | Semver версия конфига              | Да                   |
| `business-primary-keys` | Первичные ключи                    | Да                   |
| `silver-table`          | Имя Silver таблицы                 | Да                   |
| `gold-table`            | Имя Gold таблицы                   | Нет                  |
| `batch-size`            | Размер батча (1-5000)              | Нет (default: 100)   |
| `checkpoint-interval`   | Интервал checkpoint                | Нет (default: 10)    |
| `source`                | Конфиг источника                   | Нет (auto-resolved)  |
| `dq-overrides`          | Inline DQ переопределения          | Нет                  |
| `sink`                  | Конфиги слоёв (Bronze/Silver/Gold) | Нет (auto-resolved)  |
| `circuit-breaker`       | Настройки Circuit Breaker          | Нет (from base)      |
| `maintenance`           | VACUUM настройки                   | Нет (from base)      |
| `loading-strategy`      | Стратегия загрузки                 | Нет (default: full)  |
| `force-full-scan`       | Отключить checkpoint resume        | Нет (default: false) |

### Пример с переопределениями

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline-name: chembl-activity
provider: chembl
entity-type: activity
version: "1.2.0"
business-primary-keys: ["activity-id"]
silver-table: "chembl-activity"
gold-table: "chembl-activity"

# Переопределение batch-size
batch-size: 500

# Inline DQ переопределения
dq-overrides:
  field-validations:
    - field: standard-value
      type: range
      min: 0
      nullable: true
    - field: standard-type
      type: enum
      allowed: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, Kd, EC50, AC50]

# Переопределение sink (опционально)
sink:
  gold:
    partition-by: ["standard-type"]
    csv-export:
      enabled: true
      include-columns: ["activity-id", "standard-type", "standard-value"]
```

----------------------------------------------------------------------

## Composite Pipelines (ADR-026)

Composite pipelines объединяют данные из нескольких провайдеров в единый датасет.

### Структура Composite конфига

```yaml
# configs/pipelines/composite/publication.yaml
composite:
  name: composite-publication
  version: "1.1.0"

  seed:
    pipeline: chembl-publication     # Базовый пайплайн (источник ID)

  enrichers:                          # Обогащение из других провайдеров
    - pipeline: crossref-publication
      join-key: doi
      optional: true
    - pipeline: openalex-publication
      join-key: doi
      optional: true
    - pipeline: pubmed-publication
      join-key: pmid
      optional: true
    - pipeline: semanticscholar-publication
      join-key: doi
      optional: true

  merge:
    strategy: left-outer              # Сохраняем все seed записи
    conflict-resolution: prefer-seed  # При конфликте — seed выигрывает
```

### Доступные Composite Pipelines

| Composite               | Seed                 | Enrichers                                                           | Описание                      |
| ----------------------- | -------------------- | ------------------------------------------------------------------- | ----------------------------- |
| `composite-activity`    | `chembl-activity`    | enrichers                                                           | Обогащённые данные активности |
| `composite-assay`       | `chembl-assay`       | enrichers                                                           | Обогащённые данные анализов   |
| `composite-molecule`    | `chembl-molecule`    | pubchem-compound, enrichers                                         | Обогащённые молекулы          |
| `composite-publication` | `chembl-publication` | crossref, openalex, pubmed, semanticscholar                         | Обогащённые публикации        |
| `composite-target`      | `chembl-target`      | target-component, protein-class, uniprot-idmapping, uniprot-protein | Обогащённые targets           |

### Отличия от Regular Pipelines

| Аспект        | Regular Pipeline                           | Composite Pipeline                                      |
| ------------- | ------------------------------------------ | ------------------------------------------------------- |
| Корневой ключ | `pipeline-name`, `provider`, `entity-type` | `composite:`                                            |
| Source        | Один провайдер                             | Несколько провайдеров через `enrichers`                 |
| Schema        | `-schema.json`                             | Отдельная схема (ADR-026)                               |
| Пути          | Auto-computed                              | Определяются в `merge.output`                           |
| Orchestration | `PipelineRunner` + `{Entity}Transformer`   | `CompositePipelineRunner` (без отдельных трансформеров) |
| Реализация    | `application/pipelines/{provider}/`        | `application/composite/` (15 модулей)                   |

> **Архитектурная заметка:** Composite pipelines **не используют** классы трансформеров
> (`*Transformer`). Вместо этого оркестрация выполняется через `CompositePipelineRunner`,
> `EnrichmentCoordinator`, `MergeService` и другие сервисы в `application/composite/`.
> Seed и enricher pipelines запускаются как обычные single-source pipelines,
> а composite layer выполняет агрегацию на уровне Silver-данных.

----------------------------------------------------------------------

## Convention-based Path Resolution (ADR-029)

Пути и ссылки вычисляются автоматически из `provider` и `entity-type`.
Pipeline YAML файлы **не должны** явно указывать эти поля — они вычисляются
конвенционно. Если указаны явно, значение используется как override-path.

| Поле                 | Auto-computed значение                                 | Примечание                                |
| -------------------- | ------------------------------------------------------ | ----------------------------------------- |
| `source-file`        | `../../sources/{provider}.yaml`                        | Provider API settings                     |
| `dq-config-file`     | `../../quality/entities/{provider}/{entity-type}.yaml` | Informational; loader uses full hierarchy |
| `filter-config-file` | `../../filters/entities/{provider}/{entity-type}.yaml` | Informational; loader uses full hierarchy |
| `sink.bronze.path`   | `data/output/bronze/{provider}/{entity-type}`          |                                           |
| `sink.silver.path`   | `data/output/silver/{provider}/{entity-type}`          |                                           |
| `sink.gold.path`     | `data/output/gold/{provider}/{entity-type}`            |                                           |

### Авто-пропагация sort-by (ADR-014 compliance)

Параметры `sink.silver.sort-by.columns` и `sink.gold.sort-by.columns` **автоматически вычисляются** из `business-primary-keys`:

```python
# config-loader.py:155-176
if "sort-by" not in sink-silver:
    sink-silver["sort-by"] = {
        "columns": config["business-primary-keys"],
        "ascending": True,
    }
```

Это означает, что entity configs **не должны** явно указывать `sort-by` — он пропагируется из `business-primary-keys`:

```yaml
# НЕ нужно указывать sort-by — он auto-computed!
pipeline-name: chembl-activity
business-primary-keys: ["activity-id"]  # → sort-by.columns = ["activity-id"]
```

> **Преимущество:** Снижает дублирование на ~30%. Разработчик указывает только переопределения. Все 21 entity configs соответствуют ADR-014 через авто-пропагацию.

----------------------------------------------------------------------

## Data Quality (DQ) конфигурация

### Иерархическая загрузка (ADR-027)

DQ правила загружаются в порядке приоритета (позже выигрывают):

1. `configs/quality/-defaults.yaml` — глобальные defaults
1. `configs/quality/providers/{provider}.yaml` — provider-specific
1. `configs/quality/entities/{provider}/{entity}.yaml` — entity-specific
1. Inline `dq-overrides` в pipeline конфиге — финальные переопределения

> **Примечание:** Поле `dq-config-file` в pipeline YAML вычисляется конвенционно
> (ADR-029) и **не требует** явного указания. `DQConfigLoader` всегда загружает
> полную 3-уровневую иерархию по `provider`/`entity-type`. Если `dq-config-file`
> указан явно — он используется как override-path для entity-level файла.

### Специальная merge логика

- **Scalars:** Later wins
- **Validation lists:** **Concatenate** (не override)
- **Dicts:** Deep merge

### Структура DQ конфига

```yaml
# configs/quality/-defaults.yaml
thresholds:
  soft-fail: 0.05      # >5% errors → Warning
  hard-fail: 0.20      # >20% errors → Fail Batch

strict-validation: false
invalid-record-policy: quarantine  # quarantine | skip | fail

report:
  enabled: true
  format: json
  include-sample-failures: true
  sample-size: 10

common-field-validations:
  - field: -content-hash
    type: required
    nullable: false
  - field: -ingestion-ts
    type: pattern
    pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
```

### Entity-specific DQ правила

```yaml
# configs/quality/entities/chembl/activity.yaml
entity-field-validations:
  - field: activity-id
    type: required
    nullable: false
  - field: standard-value
    type: range
    min: 0
    nullable: true
  - field: standard-type
    type: enum
    allowed: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, Kd, EC50, AC50, Potency]

entity-cross-field-validations:
  - name: value-requires-units
    fields: [standard-value, standard-units]
    condition: conditional-required
    trigger-field: standard-value
    required-field: standard-units

entity-conditional-validations:
  - name: binding-requires-target
    condition-field: assay-type
    condition-value: B
    condition-operator: eq
    then-validations:
      - field: target-chembl-id
        type: required
```

### Типы валидаций

| Тип        | Описание            | Параметры                |
| ---------- | ------------------- | ------------------------ |
| `required` | Обязательное поле   | `nullable`               |
| `range`    | Числовой диапазон   | `min`, `max`, `nullable` |
| `enum`     | Допустимые значения | `allowed`, `nullable`    |
| `pattern`  | Regex паттерн       | `pattern`, `nullable`    |
| `length`   | Длина строки        | `min`, `max`             |
| `unique`   | Уникальность        | —                        |

----------------------------------------------------------------------

## Filter конфигурация

### Иерархическая загрузка (ADR-028)

Аналогично DQ, фильтры загружаются иерархически:

1. `configs/filters/-defaults.yaml`
1. `configs/filters/providers/{provider}.yaml`
1. `configs/filters/entities/{provider}/{entity}.yaml`
1. Inline `filter-rules` в pipeline конфиге

### Input Filter

Фильтрация входных данных (CSV с ID):

```yaml
input-filter:
  enabled: true
  batch-size: 100
  source-file: "data/filter-ids.csv"
  column: "molecule-id"
  api-field: "molecule-chembl-id"
```

### Gold Filters

Фильтрация данных на Gold слое:

```yaml
gold-filters:
  required-fields:
    - activity-id
    - standard-value

  columns:
    standard-type:
      operator: in
      values: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50]
    pchembl-value:
      operator: is-not-null

  ranges:
    pchembl-value:
      min: 5.0
      max: 15.0
      include-min: true
      include-max: true

  exclude-if-present:
    - deprecated-field
```

### Операторы фильтрации

| Оператор       | Описание                    |
| -------------- | --------------------------- |
| `in`           | Значение в списке           |
| `not-in`       | Значение не в списке        |
| `is-null`      | NULL                        |
| `is-not-null`  | NOT NULL                    |
| `is-empty`     | Пустая строка или список    |
| `is-not-empty` | Не пустая строка или список |

----------------------------------------------------------------------

## Source конфигурация

### Структура

```yaml
# configs/sources/chembl.yaml
source:
  type: api
  load-strategy: full
  batch-size: 20

  provider-config:
    provider: chembl
    base-url: https://www.ebi.ac.uk/chembl/api/data
    client:
      timeout-sec: 60.0
      max-retries: 3
    max-url-length: 2000
    batch-size: 20
    page-size: 1000

  circuit-breaker:
    failure-threshold: 5
    recovery-timeout: 300

  rate-limit:
    requests-per-second: 5
    burst: 10

  health-check:
    endpoint: /chembl/api/data/status
    timeout: 5

entities:
  - activity
  - assay
  - molecule
  - target
  # ... и 8 других entities для ChEMBL
```

### Rate Limits по провайдерам (7 source configs)

| Provider        | Source Config                  | Rate Limit   | Burst | Batch Size |
| --------------- | ------------------------------ | ------------ | ----- | ---------- |
| ChEMBL          | `sources/chembl.yaml`          | 5 req/sec    | 10    | 20         |
| PubChem         | `sources/pubchem.yaml`         | 5 req/sec    | 10    | 1          |
| UniProt         | `sources/uniprot.yaml`         | 100 req/sec  | 200   | 100        |
| CrossRef        | `sources/crossref.yaml`        | 10 req/sec   | 20    | 50         |
| OpenAlex        | `sources/openalex.yaml`        | 10 req/sec   | 20    | 50         |
| PubMed          | `sources/pubmed.yaml`          | 3 req/sec    | 5     | 10         |
| SemanticScholar | `sources/semanticscholar.yaml` | 100 req/5min | —     | 100        |

----------------------------------------------------------------------

## Sink конфигурация

### Структура слоёв

```yaml
sink:
  bronze:
    enabled: true
    format: jsonl
    path: data/output/bronze/chembl/activity

  silver:
    enabled: true
    format: delta
    path: data/output/silver/chembl/activity
    mode: merge                    # merge | overwrite
    primary-key: ["activity-id"]
    deterministic: true
    sort-by:
      columns: ["activity-id"]
      ascending: true
    on-schema-mismatch: evolve     # error | evolve | ignore

  gold:
    enabled: true
    format: delta                  # delta | parquet
    path: data/output/gold/chembl/activity
    mode: overwrite
    partition-by: ["standard-type"]
    flat-structure: true
    csv-export:
      enabled: true
      include-columns: ["activity-id", "standard-type", "standard-value"]
    metadata:
      owner: "data-team"
      description: "ChEMBL activity measurements"
      tags: ["bioactivity", "chembl"]
      retention-days: 365
```

### Write Modes

| Mode        | Bronze        | Silver            | Gold              |
| ----------- | ------------- | ----------------- | ----------------- |
| `append`    | Только append | —                 | —                 |
| `merge`     | —             | Upsert по PK      | —                 |
| `overwrite` | —             | Полная перезапись | Полная перезапись |

### Schema Mismatch Handling

| Режим    | Описание                                |
| -------- | --------------------------------------- |
| `error`  | Падение при несовпадении схемы          |
| `evolve` | Автоматическое добавление новых колонок |
| `ignore` | Игнорировать несовпадения               |

----------------------------------------------------------------------

## Circuit Breaker конфигурация

```yaml
circuit-breaker:
  failure-threshold: 5      # Количество ошибок для открытия
  recovery-timeout: 300     # Время recovery в секундах
  half-open-requests: 1     # Пробные запросы в half-open состоянии
```

**Состояния:**

- **Closed:** Нормальная работа
- **Open:** Все запросы блокируются
- **Half-Open:** Пробные запросы для recovery

----------------------------------------------------------------------

## Maintenance конфигурация

```yaml
maintenance:
  vacuum:
    enabled: true
    retention-days: 7           # Минимальный возраст файлов для удаления
    run-after-pipeline: false   # Автоматический VACUUM после пайплайна

  bronze-cleanup:
    enabled: true
    retention-days: 90          # Retention для Bronze файлов
```

----------------------------------------------------------------------

## Валидация конфигурации

### CLI команды

```bash
# Показать конфигурацию
bioetl config show chembl-activity

# Валидация
bioetl config validate chembl-activity

# Показать глобальные настройки
bioetl config show-settings

# Список всех пайплайнов
bioetl config list-pipelines
```

### Pydantic валидация

При загрузке конфига выполняются проверки:

| Проверка                         | Описание                                       |
| -------------------------------- | ---------------------------------------------- |
| `validate-batch-size`            | batch-size ≤ 5000                              |
| `validate-provider`              | Provider в lowercase                           |
| `validate-entity-type-canonical` | publication\* вместо document\*                |
| `validate-medallion-formats`     | Bronze→JSONL, Silver→Delta, Gold→Delta/Parquet |
| `validate-thresholds`            | soft-fail < hard-fail                          |

----------------------------------------------------------------------

## Примеры конфигураций

### Минимальный конфиг

```yaml
pipeline-name: chembl-activity
provider: chembl
entity-type: activity
version: "1.2.0"
business-primary-keys: ["activity-id"]
silver-table: "chembl-activity"
gold-table: "chembl-activity"
```

### С DQ переопределениями

```yaml
pipeline-name: chembl-activity
provider: chembl
entity-type: activity
version: "1.2.0"
business-primary-keys: ["activity-id"]
silver-table: "chembl-activity"
gold-table: "chembl-activity"

dq-overrides:
  thresholds:
    soft-fail: 0.10
    hard-fail: 0.30

  field-validations:
    - field: pchembl-value
      type: range
      min: 0
      max: 20
      nullable: true
```

### С кастомными sink путями

```yaml
pipeline-name: chembl-activity
provider: chembl
entity-type: activity
version: "1.2.0"
business-primary-keys: ["activity-id"]
silver-table: "chembl-activity"
gold-table: "chembl-activity"

sink:
  bronze:
    path: /custom/path/bronze/chembl/activity
  silver:
    path: /custom/path/silver/chembl/activity
    partition-by: ["standard-type"]
  gold:
    path: /custom/path/gold/chembl/activity
    csv-export:
      enabled: true
```

----------------------------------------------------------------------

## Миграция с JSON на YAML

> **Историческая справка:** BioETL изначально использовал JSON для конфигураций.
> Переход на YAML выполнен для улучшения читаемости и поддержки комментариев.

**Было (JSON):**

```json
{
  "pipeline-name": "chembl-activity",
  "provider": "chembl",
  "entity-type": "activity",
  "batch-size": 100
}
```

**Стало (YAML):**

```yaml
pipeline-name: chembl-activity
provider: chembl
entity-type: activity
batch-size: 100

# Комментарии теперь поддерживаются!
```

----------------------------------------------------------------------

## Troubleshooting

### Ошибка валидации конфига

```bash
bioetl config validate chembl-activity
```

**Распространённые ошибки:**

| Ошибка                   | Причина                     | Решение                |
| ------------------------ | --------------------------- | ---------------------- |
| `batch-size > 5000`      | Слишком большой batch       | Уменьшить до ≤5000     |
| `provider not lowercase` | Provider в верхнем регистре | Использовать lowercase |
| `soft-fail >= hard-fail` | Неверные пороги             | soft-fail < hard-fail  |
| `unknown field`          | Опечатка в имени поля       | Проверить spelling     |

### DQ правила не применяются

1. Проверить путь к DQ файлу:

   ```bash
   ls configs/quality/entities/{provider}/{entity}.yaml
   ```

1. Проверить merge логику — validation lists **concatenate**, не override.

1. Использовать CLI для просмотра resolved конфига:

   ```bash
   bioetl config show chembl-activity --format json
   ```

----------------------------------------------------------------------

## См. также

- [Running Pipelines](running-pipelines.md) — запуск пайплайнов
- [CLI Reference](../04-reference/cli.md) — команды CLI
- [DQ Configuration](dq-configuration.md) — детальная настройка DQ
- [ADR-014: Deterministic Writes](../../02-architecture/decisions/ADR-014-deterministic-writes.md) — sort-by requirement
- [ADR-025: Pipeline Config Unification](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md) — иерархия конфигов
- [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) — multi-provider pipelines
- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md) — иерархическая DQ загрузка
- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md) — иерархическая Filter загрузка
- [ADR-029: Convention-based Path Resolution](../02-architecture/decisions/ADR-029-output-metadata-unification.md) — авто-вычисление путей
