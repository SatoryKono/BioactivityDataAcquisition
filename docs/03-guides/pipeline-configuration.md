# Pipeline Configuration Guide

Руководство по настройке конфигурации ETL-пайплайнов в BioETL.

**Версия:** 6.0.0
**Дата обновления:** 2026-02-03

---

## Обзор

BioETL использует **YAML-файлы** для конфигурации пайплайнов. Все конфигурации валидируются через **Pydantic** при загрузке, обеспечивая типобезопасность и раннее обнаружение ошибок.

### Ключевые особенности

- **Convention over Configuration (ADR-029):** Пути и ссылки вычисляются автоматически
- **Иерархическое наследование:** Конфиги наследуют из `_base.yaml`
- **Иерархические DQ/Filter правила (ADR-027/028):** 3-уровневая иерархия с merge
- **Pydantic валидация:** Схемы проверяются при загрузке
- **Immutable Domain Objects:** Конфиги преобразуются в frozen dataclasses

---

## Структура директорий

```
configs/
├── pipelines/                    # Конфигурации пайплайнов (21 = 19 entity + 2 composite)
│   ├── _base.yaml               # Базовая конфигурация v2.0.0 (474 строки)
│   ├── _schema.json             # JSON Schema для валидации
│   ├── chembl/                  # 12 entity configs
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
│   │   ├── target.yaml
│   │   └── target_component.yaml
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
│   └── composite/               # 2 composite configs (ADR-026)
│       ├── publication.yaml     # chembl_publication + enrichers
│       └── target.yaml          # chembl_target + enrichers
├── dq/                           # Data Quality правила (21 файлов)
│   ├── _defaults.yaml           # Глобальные DQ defaults (soft_fail=0.05, hard_fail=0.20)
│   ├── providers/               # 7 provider-specific DQ
│   │   ├── chembl.yaml
│   │   ├── crossref.yaml
│   │   ├── openalex.yaml
│   │   ├── pubchem.yaml
│   │   ├── pubmed.yaml
│   │   ├── semanticscholar.yaml
│   │   └── uniprot.yaml
│   └── entities/                # 14 entity-specific DQ
│       ├── chembl/
│       │   ├── activity.yaml
│       │   ├── assay.yaml
│       │   └── ...              # 12 entity DQ configs
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

| Категория | Количество | Описание |
|-----------|------------|----------|
| Pipeline configs (entity) | 19 | Regular ETL pipelines |
| Composite configs | 2 | Multi-provider pipelines (ADR-026) |
| DQ configs | 21 | 1 defaults + 7 providers + 13 entities |
| Filter configs | 8 | 1 defaults + 7 providers |
| Source configs | 7 | Один на провайдера |
| **Итого** | **58** | Все конфиги валидированы |

---

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

| Секция | Описание | Обязательно |
|--------|----------|-------------|
| `pipeline_name` | Уникальный идентификатор пайплайна | Да |
| `provider` | Имя провайдера (lowercase) | Да |
| `entity_type` | Тип сущности | Да |
| `version` | Semver версия конфига | Да |
| `primary_keys` | Первичные ключи | Да |
| `silver_table` | Имя Silver таблицы | Да |
| `gold_table` | Имя Gold таблицы | Нет |
| `batch_size` | Размер батча (1-5000) | Нет (default: 100) |
| `checkpoint_interval` | Интервал checkpoint | Нет (default: 10) |
| `source` | Конфиг источника | Нет (auto-resolved) |
| `dq_rules` | Inline DQ переопределения | Нет |
| `sink` | Конфиги слоёв (Bronze/Silver/Gold) | Нет (auto-resolved) |
| `circuit_breaker` | Настройки Circuit Breaker | Нет (from base) |
| `maintenance` | VACUUM настройки | Нет (from base) |
| `loading_strategy` | Стратегия загрузки | Нет (default: full) |
| `force_full_scan` | Отключить checkpoint resume | Нет (default: false) |

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
dq_rules:
  field_validations:
    - field: standard_value
      type: range
      min: 0
      nullable: true
    - field: standard_type
      type: enum
      allowed: [IC50, Ki, Kd, EC50, AC50]

# Переопределение sink (опционально)
sink:
  gold:
    partition_by: ["standard_type"]
    csv_export:
      enabled: true
      include_columns: ["activity_id", "standard_type", "standard_value"]
```

---

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

| Composite | Seed | Enrichers | Описание |
|-----------|------|-----------|----------|
| `composite_publication` | `chembl_publication` | crossref, openalex, pubmed, semanticscholar | Обогащённые публикации |
| `composite_target` | `chembl_target` | target_component, protein_class, uniprot_idmapping, uniprot_protein | Обогащённые targets |

### Отличия от Regular Pipelines

| Аспект | Regular Pipeline | Composite Pipeline |
|--------|------------------|-------------------|
| Корневой ключ | `pipeline_name`, `provider`, `entity_type` | `composite:` |
| Source | Один провайдер | Несколько провайдеров через `enrichers` |
| Schema | `_schema.json` | Отдельная схема (ADR-026) |
| Пути | Auto-computed | Определяются в `merge.output` |

---

## Convention-based Path Resolution (ADR-029)

Пути и ссылки вычисляются автоматически из `provider` и `entity_type`:

| Поле | Auto-computed значение |
|------|------------------------|
| `source_file` | `../../sources/{provider}.yaml` |
| `dq_config_file` | `../../dq/entities/{provider}/{entity_type}.yaml` |
| `filter_config_file` | `../../filter/entities/{provider}/{entity_type}.yaml` |
| `sink.bronze.path` | `data/output/bronze/{provider}/{entity_type}` |
| `sink.silver.path` | `data/output/silver/{provider}/{entity_type}` |
| `sink.gold.path` | `data/output/gold/{provider}/{entity_type}` |

### Авто-пропагация sort_by (ADR-014 compliance)

Параметры `sink.silver.sort_by.columns` и `sink.gold.sort_by.columns` **автоматически вычисляются** из `primary_keys`:

```python
# config_loader.py:155-176
if "sort_by" not in sink_silver:
    sink_silver["sort_by"] = {
        "columns": config["primary_keys"],
        "ascending": True
    }
```

Это означает, что entity configs **не должны** явно указывать `sort_by` — он пропагируется из `primary_keys`:

```yaml
# НЕ нужно указывать sort_by — он auto-computed!
pipeline_name: chembl_activity
primary_keys: ["activity_id"]  # → sort_by.columns = ["activity_id"]
```

> **Преимущество:** Снижает дублирование на ~30%. Разработчик указывает только переопределения. Все 19 entity configs соответствуют ADR-014 через авто-пропагацию.

---

## Data Quality (DQ) конфигурация

### Иерархическая загрузка (ADR-027)

DQ правила загружаются в порядке приоритета (позже выигрывают):

1. `configs/dq/_defaults.yaml` — глобальные defaults
2. `configs/dq/providers/{provider}.yaml` — provider-specific
3. `configs/dq/entities/{provider}/{entity}.yaml` — entity-specific
4. Inline `dq_rules` в pipeline конфиге — финальные переопределения

### Специальная merge логика

- **Scalars:** Later wins
- **Validation lists:** **Concatenate** (не override)
- **Dicts:** Deep merge

### Структура DQ конфига

```yaml
# configs/dq/_defaults.yaml
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
# configs/dq/entities/chembl/activity.yaml
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
    allowed: [IC50, Ki, Kd, EC50, AC50, Potency]

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

| Тип | Описание | Параметры |
|-----|----------|-----------|
| `required` | Обязательное поле | `nullable` |
| `range` | Числовой диапазон | `min`, `max`, `nullable` |
| `enum` | Допустимые значения | `allowed`, `nullable` |
| `pattern` | Regex паттерн | `pattern`, `nullable` |
| `length` | Длина строки | `min`, `max` |
| `unique` | Уникальность | — |

---

## Filter конфигурация

### Иерархическая загрузка (ADR-028)

Аналогично DQ, фильтры загружаются иерархически:

1. `configs/filter/_defaults.yaml`
2. `configs/filter/providers/{provider}.yaml`
3. `configs/filter/entities/{provider}/{entity}.yaml`
4. Inline `filter_rules` в pipeline конфиге

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
      values: [IC50, Ki]
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

| Оператор | Описание |
|----------|----------|
| `in` | Значение в списке |
| `not_in` | Значение не в списке |
| `is_null` | NULL |
| `is_not_null` | NOT NULL |
| `is_empty` | Пустая строка или список |
| `is_not_empty` | Не пустая строка или список |

---

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
    endpoint: /chembl/api/data/status.json
    timeout: 5

entities:
  - activity
  - assay
  - molecule
  - target
  # ... и 8 других entities для ChEMBL
```

### Rate Limits по провайдерам (7 source configs)

| Provider | Source Config | Rate Limit | Burst | Batch Size |
|----------|---------------|------------|-------|------------|
| ChEMBL | `sources/chembl.yaml` | 5 req/sec | 10 | 20 |
| PubChem | `sources/pubchem.yaml` | 5 req/sec | 10 | 1 |
| UniProt | `sources/uniprot.yaml` | 100 req/sec | 200 | 100 |
| CrossRef | `sources/crossref.yaml` | 10 req/sec | 20 | 50 |
| OpenAlex | `sources/openalex.yaml` | 10 req/sec | 20 | 50 |
| PubMed | `sources/pubmed.yaml` | 3 req/sec | 5 | 10 |
| SemanticScholar | `sources/semanticscholar.yaml` | 100 req/5min | — | 100 |

---

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
    mode: overwrite
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

| Mode | Bronze | Silver | Gold |
|------|--------|--------|------|
| `append` | Только append | — | — |
| `merge` | — | Upsert по PK | — |
| `overwrite` | — | Полная перезапись | Полная перезапись |

### Schema Mismatch Handling

| Режим | Описание |
|-------|----------|
| `error` | Падение при несовпадении схемы |
| `evolve` | Автоматическое добавление новых колонок |
| `ignore` | Игнорировать несовпадения |

---

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

---

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

---

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

| Проверка | Описание |
|----------|----------|
| `validate_batch_size` | batch_size ≤ 5000 |
| `validate_provider` | Provider в lowercase |
| `validate_entity_type_canonical` | publication* вместо document* |
| `validate_medallion_formats` | Bronze→JSONL, Silver→Delta, Gold→Delta/Parquet |
| `validate_thresholds` | soft_fail < hard_fail |

---

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

dq_rules:
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

---

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

---

## Troubleshooting

### Ошибка валидации конфига

```bash
bioetl config validate chembl_activity
```

**Распространённые ошибки:**

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `batch_size > 5000` | Слишком большой batch | Уменьшить до ≤5000 |
| `provider not lowercase` | Provider в верхнем регистре | Использовать lowercase |
| `soft_fail >= hard_fail` | Неверные пороги | soft_fail < hard_fail |
| `unknown field` | Опечатка в имени поля | Проверить spelling |

### DQ правила не применяются

1. Проверить путь к DQ файлу:
   ```bash
   ls configs/dq/entities/{provider}/{entity}.yaml
   ```

2. Проверить merge логику — validation lists **concatenate**, не override.

3. Использовать CLI для просмотра resolved конфига:
   ```bash
   bioetl config show chembl_activity --format json
   ```

---

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
