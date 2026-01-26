# Pipeline Configuration Guide

Руководство по настройке конфигурации ETL-пайплайнов в BioETL.

**Версия:** 5.9.0
**Дата обновления:** 2026-01-26

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
├── pipelines/                    # Конфигурации пайплайнов
│   ├── _base.yaml               # Базовая конфигурация (472 строки)
│   ├── chembl/
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   ├── molecule.yaml
│   │   └── ...
│   ├── pubchem/
│   │   └── compound.yaml
│   └── uniprot/
│       └── protein.yaml
├── dq/                           # Data Quality правила
│   ├── _defaults.yaml           # Глобальные DQ defaults
│   ├── providers/
│   │   └── chembl.yaml          # Provider-specific DQ
│   └── entities/
│       └── chembl/
│           └── activity.yaml    # Entity-specific DQ
├── filter/                       # Фильтры данных
│   ├── _defaults.yaml
│   ├── providers/
│   └── entities/
└── sources/                      # Конфигурации источников
    ├── chembl.yaml
    ├── pubchem.yaml
    └── uniprot.yaml
```

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

> **Преимущество:** Снижает дублирование на ~30%. Разработчик указывает только переопределения.

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
```

### Rate Limits по провайдерам

| Provider | Rate Limit | Burst |
|----------|------------|-------|
| ChEMBL | 5 req/sec | 10 |
| PubChem | 5 req/sec | 10 |
| UniProt | 100 req/sec (with API key) | 200 |
| CrossRef | 10 req/sec | 20 |
| OpenAlex | 10 req/sec | 20 |
| PubMed | 3 req/sec | 5 |
| SemanticScholar | 100 req/5min | — |

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
python -m bioetl.main config show chembl_activity

# Валидация
python -m bioetl.main config validate chembl_activity

# Показать глобальные настройки
python -m bioetl.main config show-settings

# Список всех пайплайнов
python -m bioetl.main config list-pipelines
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
python -m bioetl.main config validate chembl_activity
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
   python -m bioetl.main config show chembl_activity --format json
   ```

---

## См. также

- [Running Pipelines](running-pipelines.md) — запуск пайплайнов
- [CLI Reference](../04-reference/cli.md) — команды CLI
- [DQ Configuration](dq-configuration.md) — детальная настройка DQ
- [ADR-029: Convention-based Path Resolution](../02-architecture/decisions/ADR-029-output-metadata-unification.md)
- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
