# Pipeline Configuration Guide

Руководство по настройке конфигурации ETL-пайплайнов в BioETL.

**Версия:** 6.0.0
**Дата обновления:** 2026-02-03

______________________________________________________________________

## Обзор

BioETL использует **YAML-файлы** для конфигурации пайплайнов. Все конфигурации валидируются через **Pydantic** при загрузке, обеспечивая типобезопасность и раннее обнаружение ошибок.

### Ключевые особенности

- **Convention over Configuration (ADR-029):** Пути и ссылки вычисляются автоматически
- **Иерархическое наследование:** Конфиги наследуют из `_base.yaml`
- **Иерархические DQ/Filter правила (ADR-027/028):** 3-уровневая иерархия с merge
- **Pydantic валидация:** Схемы проверяются при загрузке
- **Immutable Domain Objects:** Конфиги преобразуются в frozen dataclasses

______________________________________________________________________

## Структура директорий

```
configs/
├── pipelines/                    # Конфигурации пайплайнов (26 = 21 entity + 5 composite)
│   ├── _base.yaml               # Базовая конфигурация v2.1.0 (491 строка)
│   ├── _schema.json             # JSON Schema для валидации
│   ├── chembl/                  # 14 entity configs
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   ├── assay_parameters.yaml
│   │   ├── cell_line.yaml
│   │   ├── compound_record.yaml
│   │   ├── molecule.yaml
│   │   ├── protein_class.yaml
│   │   ├── publication.yaml
│   │   ├── publication_similarity.yaml
│   │   ├── publication_term.yaml
│   │   ├── subcellular_fraction.yaml
│   │   ├── target.yaml
│   │   ├── target_component.yaml
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
│       ├── activity.yaml        # chembl_activity + enrichers
│       ├── assay.yaml           # chembl_assay + enrichers
│       ├── molecule.yaml        # chembl_molecule + enrichers
│       ├── publication.yaml     # chembl_publication + enrichers
│       └── target.yaml          # chembl_target + enrichers
├── dq/                           # Data Quality правила (31 файл)
│   ├── _defaults.yaml           # Глобальные DQ defaults (soft_fail=0.05, hard_fail=0.20)
│   ├── providers/               # 7 provider-specific DQ
│   │   ├── chembl.yaml
│   │   ├── crossref.yaml
│   │   ├── openalex.yaml
│   │   ├── pubchem.yaml
│   │   ├── pubmed.yaml
│   │   ├── semanticscholar.yaml
│   │   └── uniprot.yaml
│   └── entities/                # 22 entity-specific DQ
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
├── filter/                       # Фильтры данных (8 файлов)
│   ├── _defaults.yaml           # batch_size: 100
│   └── providers/               # Provider-specific batch_sizes
│       ├── chembl.yaml
│       ├── crossref.yaml
│       ├── openalex.yaml
│       ├── pubchem.yaml
│       ├── pubmed.yaml
│       ├── semanticscholar.yaml
│       └── uniprot.yaml
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

| Категория                 | Количество | Описание                                          |
| ------------------------- | ---------- | ------------------------------------------------- |
| Pipeline configs (entity) | 21         | Regular ETL pipelines                             |
| Composite configs         | 5          | Multi-provider pipelines (ADR-026)                |
| DQ configs                | 31         | 1 defaults + 7 providers + 22 entities + 1 schema |
| Filter configs            | 8          | 1 defaults + 7 providers                          |
| Source configs            | 7          | Один на провайдера                                |
| **Итого**                 | **71**     | Все конфиги валидированы                          |

______________________________________________________________________

## Pipeline YAML конфиг

### Минимальный конфиг

Благодаря наследованию из `_base.yaml`, минимальный конфиг содержит только переопределения:

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"
```

### Полная структура конфига

| Секция                | Описание                           | Обязательно          |
| --------------------- | ---------------------------------- | -------------------- |
| `pipeline_name`       | Уникальный идентификатор пайплайна | Да                   |
| `provider`            | Имя провайдера (lowercase)         | Да                   |
| `entity_type`         | Тип сущности                       | Да                   |
| `version`             | Semver версия конфига              | Да                   |
| `primary_keys`        | Первичные ключи                    | Да                   |
| `silver_table`        | Имя Silver таблицы                 | Да                   |
| `gold_table`          | Имя Gold таблицы                   | Нет                  |
| `batch_size`          | Размер батча (1-5000)              | Нет (default: 100)   |
| `checkpoint_interval` | Интервал checkpoint                | Нет (default: 10)    |
| `source`              | Конфиг источника                   | Нет (auto-resolved)  |
| `dq_overrides`        | Inline DQ переопределения          | Нет                  |
| `sink`                | Конфиги слоёв (Bronze/Silver/Gold) | Нет (auto-resolved)  |
| `circuit_breaker`     | Настройки Circuit Breaker          | Нет (from base)      |
| `maintenance`         | VACUUM настройки                   | Нет (from base)      |
| `loading_strategy`    | Стратегия загрузки                 | Нет (default: full)  |
| `force_full_scan`     | Отключить checkpoint resume        | Нет (default: false) |

### Пример с переопределениями

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

# Переопределение batch_size
batch_size: 500

# Inline DQ переопределения
dq_overrides:
  field_validations:
    - field: standard_value
      type: range
      min: 0
      nullable: true
    - field: standard_type
      type: enum
      allowed: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, Kd, EC50, AC50]

# Переопределение sink (опционально)
sink:
  gold:
    partition_by: ["standard_type"]
    csv_export:
      enabled: true
      include_columns: ["activity_id", "standard_type", "standard_value"]
```

______________________________________________________________________

## Composite Pipelines (ADR-026)

Composite pipelines объединяют данные из нескольких провайдеров в единый датасет.

### Структура Composite конфига

```yaml
# configs/pipelines/composite/publication.yaml
composite:
  name: composite_publication
  version: "1.1.0"

  seed:
    pipeline: chembl_publication     # Базовый пайплайн (источник ID)

  enrichers:                          # Обогащение из других провайдеров
    - pipeline: crossref_publication
      join_key: doi
      optional: true
    - pipeline: openalex_publication
      join_key: doi
      optional: true
    - pipeline: pubmed_publication
      join_key: pmid
      optional: true
    - pipeline: semanticscholar_publication
      join_key: doi
      optional: true

  merge:
    strategy: left_outer              # Сохраняем все seed записи
    conflict_resolution: prefer_seed  # При конфликте — seed выигрывает
```

### Доступные Composite Pipelines

| Composite               | Seed                 | Enrichers                                                           | Описание                      |
| ----------------------- | -------------------- | ------------------------------------------------------------------- | ----------------------------- |
| `composite_activity`    | `chembl_activity`    | enrichers                                                           | Обогащённые данные активности |
| `composite_assay`       | `chembl_assay`       | enrichers                                                           | Обогащённые данные анализов   |
| `composite_molecule`    | `chembl_molecule`    | pubchem_compound, enrichers                                         | Обогащённые молекулы          |
| `composite_publication` | `chembl_publication` | crossref, openalex, pubmed, semanticscholar                         | Обогащённые публикации        |
| `composite_target`      | `chembl_target`      | target_component, protein_class, uniprot_idmapping, uniprot_protein | Обогащённые targets           |

### Отличия от Regular Pipelines

| Аспект        | Regular Pipeline                           | Composite Pipeline                                      |
| ------------- | ------------------------------------------ | ------------------------------------------------------- |
| Корневой ключ | `pipeline_name`, `provider`, `entity_type` | `composite:`                                            |
| Source        | Один провайдер                             | Несколько провайдеров через `enrichers`                 |
| Schema        | `_schema.json`                             | Отдельная схема (ADR-026)                               |
| Пути          | Auto-computed                              | Определяются в `merge.output`                           |
| Orchestration | `PipelineRunner` + `{Entity}Transformer`   | `CompositePipelineRunner` (без отдельных трансформеров) |
| Реализация    | `application/pipelines/{provider}/`        | `application/composite/` (15 модулей)                   |

> **Архитектурная заметка:** Composite pipelines **не используют** классы трансформеров
> (`*Transformer`). Вместо этого оркестрация выполняется через `CompositePipelineRunner`,
> `EnrichmentCoordinator`, `MergeService` и другие сервисы в `application/composite/`.
> Seed и enricher pipelines запускаются как обычные single-source pipelines,
> а composite layer выполняет агрегацию на уровне Silver-данных.

______________________________________________________________________

## Convention-based Path Resolution (ADR-029)

Пути и ссылки вычисляются автоматически из `provider` и `entity_type`:

| Поле                 | Auto-computed значение                                 |
| -------------------- | ------------------------------------------------------ |
| `source_file`        | `../../sources/{provider}.yaml`                        |
| `dq_config_file`     | `../../quality/entities/{provider}/{entity_type}.yaml` |
| `filter_config_file` | `../../filters/entities/{provider}/{entity_type}.yaml` |
| `sink.bronze.path`   | `data/output/bronze/{provider}/{entity_type}`          |
| `sink.silver.path`   | `data/output/silver/{provider}/{entity_type}`          |
| `sink.gold.path`     | `data/output/gold/{provider}/{entity_type}`            |

### Авто-пропагация sort_by (ADR-014 compliance)

Параметры `sink.silver.sort_by.columns` и `sink.gold.sort_by.columns` **автоматически вычисляются** из `primary_keys`:

```python
# config_loader.py:155-176
if "sort_by" not in sink_silver:
    sink_silver["sort_by"] = {"columns": config["primary_keys"], "ascending": True}
```

Это означает, что entity configs **не должны** явно указывать `sort_by` — он пропагируется из `primary_keys`:

```yaml
# НЕ нужно указывать sort_by — он auto-computed!
pipeline_name: chembl_activity
primary_keys: ["activity_id"]  # → sort_by.columns = ["activity_id"]
```

> **Преимущество:** Снижает дублирование на ~30%. Разработчик указывает только переопределения. Все 21 entity configs соответствуют ADR-014 через авто-пропагацию.

______________________________________________________________________

## Data Quality (DQ) конфигурация

### Иерархическая загрузка (ADR-027)

DQ правила загружаются в порядке приоритета (позже выигрывают):

1. `configs/quality/_defaults.yaml` — глобальные defaults
1. `configs/quality/providers/{provider}.yaml` — provider-specific
1. `configs/quality/entities/{provider}/{entity}.yaml` — entity-specific
1. Inline `dq_overrides` в pipeline конфиге — финальные переопределения

### Специальная merge логика

- **Scalars:** Later wins
- **Validation lists:** **Concatenate** (не override)
- **Dicts:** Deep merge

### Структура DQ конфига

```yaml
# configs/quality/_defaults.yaml
thresholds:
  soft_fail: 0.05      # >5% errors → Warning
  hard_fail: 0.20      # >20% errors → Fail Batch

strict_validation: false
invalid_record_policy: quarantine  # quarantine | skip | fail

report:
  enabled: true
  format: json
  include_sample_failures: true
  sample_size: 10

common_field_validations:
  - field: _content_hash
    type: required
    nullable: false
  - field: _ingestion_ts
    type: pattern
    pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
```

### Entity-specific DQ правила

```yaml
# configs/quality/entities/chembl/activity.yaml
entity_field_validations:
  - field: activity_id
    type: required
    nullable: false
  - field: standard_value
    type: range
    min: 0
    nullable: true
  - field: standard_type
    type: enum
    allowed: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, Kd, EC50, AC50, Potency]

entity_cross_field_validations:
  - name: value_requires_units
    fields: [standard_value, standard_units]
    condition: conditional_required
    trigger_field: standard_value
    required_field: standard_units

entity_conditional_validations:
  - name: binding_requires_target
    condition_field: assay_type
    condition_value: B
    condition_operator: eq
    then_validations:
      - field: target_chembl_id
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

______________________________________________________________________

## Filter конфигурация

### Иерархическая загрузка (ADR-028)

Аналогично DQ, фильтры загружаются иерархически:

1. `configs/filters/_defaults.yaml`
1. `configs/filters/providers/{provider}.yaml`
1. `configs/filters/entities/{provider}/{entity}.yaml`
1. Inline `filter_rules` в pipeline конфиге

### Input Filter

Фильтрация входных данных (CSV с ID):

```yaml
input_filter:
  enabled: true
  batch_size: 100
  source_file: "data/filter_ids.csv"
  column: "molecule_id"
  api_field: "molecule_chembl_id"
```

### Gold Filters

Фильтрация данных на Gold слое:

```yaml
gold_filters:
  required_fields:
    - activity_id
    - standard_value

  columns:
    standard_type:
      operator: in
      values: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50]
    pchembl_value:
      operator: is_not_null

  ranges:
    pchembl_value:
      min: 5.0
      max: 15.0
      include_min: true
      include_max: true

  exclude_if_present:
    - deprecated_field
```

### Операторы фильтрации

| Оператор       | Описание                    |
| -------------- | --------------------------- |
| `in`           | Значение в списке           |
| `not_in`       | Значение не в списке        |
| `is_null`      | NULL                        |
| `is_not_null`  | NOT NULL                    |
| `is_empty`     | Пустая строка или список    |
| `is_not_empty` | Не пустая строка или список |

______________________________________________________________________

## Source конфигурация

### Структура

```yaml
# configs/sources/chembl.yaml
source:
  type: api
  load_strategy: full
  batch_size: 20

  provider_config:
    provider: chembl
    base_url: https://www.ebi.ac.uk/chembl/api/data
    client:
      timeout_sec: 60.0
      max_retries: 3
    max_url_length: 2000
    batch_size: 20
    page_size: 1000

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300

  rate_limit:
    requests_per_second: 5
    burst: 10

  health_check:
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

______________________________________________________________________

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
    mode: merge                    # merge | append | delete
    primary_key: ["activity_id"]
    deterministic: true
    sort_by:
      columns: ["activity_id"]
      ascending: true
    on_schema_mismatch: evolve     # error | evolve | ignore

  gold:
    enabled: true
    format: delta                  # delta | parquet
    path: data/output/gold/chembl/activity
    mode: scd2
    scd_config:
      valid_from: _valid_from
      valid_to: _valid_to
      is_current: _is_current
      version: _version
    partition_by: ["standard_type"]
    flat_structure: true
    csv_export:
      enabled: true
      include_columns: ["activity_id", "standard_type", "standard_value"]
    metadata:
      owner: "data-team"
      description: "ChEMBL activity measurements"
      tags: ["bioactivity", "chembl"]
      retention_days: 365
```

### Write Modes

| Mode        | Bronze        | Silver                      | Gold                                                             |
| ----------- | ------------- | --------------------------- | ---------------------------------------------------------------- |
| `append`    | Только append | Вставка без upsert          | Фактовые потоки без ретро-исправлений                            |
| `merge`     | —             | Upsert по PK                | —                                                                |
| `delete`    | —             | Полная перезапись (rebuild) | —                                                                |
| `scd2`      | —             | —                           | Историчность (`valid_from`, `valid_to`, `is_current`, `version`) |
| `overwrite` | —             | —                           | Полная перезапись пересчитываемых витрин                         |

### Criteria for history retention (Gold)

- **Reference dictionaries** -> `mode: scd2`
- **Slowly evolving records** -> `mode: scd2`
- **Publication metadata** -> `mode: scd2`
- **Recomputed derived outputs** -> `mode: overwrite`

Gold mode must be explicit in each pipeline YAML (`sink.gold.mode`).

| Entity                                                                                                                                | Current Mode         | Recommended Mode     | Breaking | Migration                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- | -------- | ----------------------------------------------------------- |
| publication (chembl/pubmed/crossref/openalex/semanticscholar)                                                                         | implicit `overwrite` | `scd2`               | Yes      | Bootstrap snapshot, then SCD2 + backfill validity intervals |
| reference dictionaries (chembl: assay, assay_parameters, cell_line, tissue, protein_class, subcellular_fraction)                      | implicit `overwrite` | `scd2`               | Yes      | Rebuild once and enable versioned updates                   |
| slowly evolving records (chembl: target, target_component, molecule, compound_record; uniprot: protein, idmapping; pubchem: compound) | implicit `overwrite` | `scd2`               | Yes      | Initialize as version=1, future updates create new versions |
| high-volume facts (chembl: activity)                                                                                                  | implicit `overwrite` | `append`             | No       | Set explicit append mode                                    |
| recomputed derived outputs (chembl: publication_similarity, publication_term)                                                         | implicit `overwrite` | explicit `overwrite` | No       | Keep overwrite but declare explicitly                       |

### Schema Mismatch Handling

| Режим    | Описание                                |
| -------- | --------------------------------------- |
| `error`  | Падение при несовпадении схемы          |
| `evolve` | Автоматическое добавление новых колонок |
| `ignore` | Игнорировать несовпадения               |

______________________________________________________________________

## Circuit Breaker конфигурация

```yaml
circuit_breaker:
  failure_threshold: 5      # Количество ошибок для открытия
  recovery_timeout: 300     # Время recovery в секундах
  half_open_requests: 1     # Пробные запросы в half-open состоянии
```

**Состояния:**

- **Closed:** Нормальная работа
- **Open:** Все запросы блокируются
- **Half-Open:** Пробные запросы для recovery

______________________________________________________________________

## Maintenance конфигурация

```yaml
maintenance:
  vacuum:
    enabled: true
    retention_days: 7           # Минимальный возраст файлов для удаления
    run_after_pipeline: false   # Автоматический VACUUM после пайплайна

  bronze_cleanup:
    enabled: true
    retention_days: 90          # Retention для Bronze файлов
```

______________________________________________________________________

## Валидация конфигурации

### CLI команды

```bash
# Показать конфигурацию
bioetl config show chembl_activity

# Валидация
bioetl config validate chembl_activity

# Показать глобальные настройки
bioetl config show-settings

# Список всех пайплайнов
bioetl config list-pipelines
```

### Pydantic валидация

При загрузке конфига выполняются проверки:

| Проверка                         | Описание                                       |
| -------------------------------- | ---------------------------------------------- |
| `validate_batch_size`            | batch_size ≤ 5000                              |
| `validate_provider`              | Provider в lowercase                           |
| `validate_entity_type_canonical` | publication\* вместо document\*                |
| `validate_medallion_formats`     | Bronze→JSONL, Silver→Delta, Gold→Delta/Parquet |
| `validate_thresholds`            | soft_fail < hard_fail                          |

______________________________________________________________________

## Примеры конфигураций

### Минимальный конфиг

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"
```

### С DQ переопределениями

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

dq_overrides:
  thresholds:
    soft_fail: 0.10
    hard_fail: 0.30

  field_validations:
    - field: pchembl_value
      type: range
      min: 0
      max: 20
      nullable: true
```

### С кастомными sink путями

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

sink:
  bronze:
    path: /custom/path/bronze/chembl/activity
  silver:
    path: /custom/path/silver/chembl/activity
    partition_by: ["standard_type"]
  gold:
    path: /custom/path/gold/chembl/activity
    csv_export:
      enabled: true
```

______________________________________________________________________

## Миграция с JSON на YAML

> **Историческая справка:** BioETL изначально использовал JSON для конфигураций.
> Переход на YAML выполнен для улучшения читаемости и поддержки комментариев.

**Было (JSON):**

```json
{
  "pipeline_name": "chembl_activity",
  "provider": "chembl",
  "entity_type": "activity",
  "batch_size": 100
}
```

**Стало (YAML):**

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
batch_size: 100

# Комментарии теперь поддерживаются!
```

______________________________________________________________________

## Troubleshooting

### Ошибка валидации конфига

```bash
bioetl config validate chembl_activity
```

**Распространённые ошибки:**

| Ошибка                   | Причина                     | Решение                |
| ------------------------ | --------------------------- | ---------------------- |
| `batch_size > 5000`      | Слишком большой batch       | Уменьшить до ≤5000     |
| `provider not lowercase` | Provider в верхнем регистре | Использовать lowercase |
| `soft_fail >= hard_fail` | Неверные пороги             | soft_fail < hard_fail  |
| `unknown field`          | Опечатка в имени поля       | Проверить spelling     |

### DQ правила не применяются

1. Проверить путь к DQ файлу:

   ```bash
   ls configs/quality/entities/{provider}/{entity}.yaml
   ```

1. Проверить merge логику — validation lists **concatenate**, не override.

1. Использовать CLI для просмотра resolved конфига:

   ```bash
   bioetl config show chembl_activity --format json
   ```

______________________________________________________________________

## См. также

- [Running Pipelines](running-pipelines.md) — запуск пайплайнов
- [CLI Reference](../04-reference/cli.md) — команды CLI
- [DQ Configuration](dq-configuration.md) — детальная настройка DQ
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md) — sort_by requirement
- [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md) — иерархия конфигов
- [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) — multi-provider pipelines
- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md) — иерархическая DQ загрузка
- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md) — иерархическая Filter загрузка
- [ADR-029: Convention-based Path Resolution](../02-architecture/decisions/ADR-029-output-metadata-unification.md) — авто-вычисление путей
