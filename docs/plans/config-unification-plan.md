# Config Unification: Аудит и План Рефакторинга

*Дата: 2026-02-24 | Версия: 1.0.0*
*Автор: Claude Code (аудит по запросу)*

---

## 0. Актуализация Плана (2026-02-24)

- Текущий факт (после Phase 1/2 backward-compat): в `configs/` **162 YAML**.
- RF-CFG-001, RF-CFG-002 и RF-CFG-005 уже выполнены в текущем коде.
- RF-CFG-003 выполнен: явный `schema_file` удален из стандартных pipeline config'ов (остается convention-default).
- В плане была внутренняя коллизия по `batch_size` (Phase 0 vs §5.2): принято корректное решение из RF-CFG-004 (**SKIPPED**), т.к. `pipeline.batch_size` и `input_filter.batch_size` относятся к разным уровням.
- RF-CFG-043 требует корректировки номера ADR: **ADR-033 уже занят**, использовать следующий свободный номер.
- RF-CFG-010..015 реализованы (base-консолидация + fallback).
- RF-CFG-020..024 реализованы в backward-compat режиме (новые `configs/providers/*.yaml` + fallback на legacy paths).
- RF-CFG-030 выполнен для **всех standard pipelines (21/21)**: добавлены unified entity files в `configs/entities/{provider}/{entity}.yaml` для `chembl`, `crossref`, `openalex`, `pubchem`, `pubmed`, `semanticscholar`, `uniprot`.
- RF-CFG-032 выполнен в backward-compat режиме: `load_pipeline_config()` и секционные loaders читают unified entity sections (`pipeline/schema/quality/filters/contracts`) с fallback на legacy paths.
- RF-CFG-033 пока **не завершен**: `PipelineContractPolicyLoader` сохранен и переведен на режим unified-first + legacy fallback.
- Технический эффект Phase 3: `DQConfigLoader` вырос до 322 LOC; добавлены явные архитектурные exemptions в `tests/architecture/test_code_metrics.py` как переходная мера до декомпозиции (RF-CFG-031/RF-CFG-037).
- RF-CFG-036 выполнен: composite configs перенесены в `configs/composites/*.yaml`, `load_composite_config()` переведен на new-first path (`configs/composites`) с legacy fallback (`configs/pipelines/composite`).
- RF-CFG-037 выполнен: 3 реализации `deep_merge` унифицированы через `src/bioetl/infrastructure/config_merge.py::config_merge` с параметризуемыми list-стратегиями (concat keys, resolver-based merge для DQ validations).

---

## 1. Результаты Аудита

### 1.1 Текущая Статистика

| Метрика | Значение |
|---------|----------|
| Всего YAML файлов в `configs/` | **162** |
| JSON Schema файлов | 2 |
| Категорий конфигов | 9 (pipelines, sources, schemas, quality, filters, contracts, hash_policy, enums, naming) |
| Файлов на 1 стандартный pipeline | **11** |
| Файлов на 1 composite pipeline | **8-12** |
| Базовых/общих файлов | 5 (`_base.yaml` × 3, `_schema/` × 2) |

### 1.2 Файлы, Загружаемые для Одного Pipeline

Пример: `chembl_activity` — **11 файлов**:

| # | Файл | Тип | Роль |
|---|------|-----|------|
| 1 | `pipelines/_base.yaml` | BASE | Pipeline execution defaults |
| 2 | `pipelines/chembl/activity.yaml` | ENTITY | Pipeline identity + overrides |
| 3 | `sources/chembl.yaml` | PROVIDER | API connection, rate limits |
| 4 | `schemas/chembl/activity.yaml` | ENTITY | Column groups, content_hash |
| 5 | `contracts/pipelines/chembl/activity.yaml` | ENTITY | PK, merge_keys, rename_map |
| 6 | `quality/_defaults.yaml` | BASE | DQ thresholds, common validations |
| 7 | `quality/providers/chembl.yaml` | PROVIDER | ChEMBL ID pattern validations |
| 8 | `quality/entities/chembl/activity.yaml` | ENTITY | Activity DQ rules |
| 9 | `filters/_defaults.yaml` | BASE | Filter structure template |
| 10 | `filters/providers/chembl.yaml` | PROVIDER | batch_size override |
| 11 | `filters/entities/chembl/activity.yaml` | ENTITY | extraction_params, silver/gold filters |

**Итого:** 3 BASE + 2 PROVIDER + 6 ENTITY = 11 файлов.

### 1.3 Обнаруженные Проблемы

#### P-001: Массивная Избыточность в Contracts (CRITICAL)

Файл `contracts/pipelines/{provider}/{entity}.yaml` на **80% идентичен** у всех 21 pipeline:

```yaml
# ОДИНАКОВО у ВСЕХ 21 entity:
rename_map:
  run_id: _run_id
  run_type: _run_type
  source_batch_id: _source_batch_id
  ingestion_ts: _ingestion_ts
  source: _source
hash_include: []
hash_exclude:
  - _ingestion_ts
  - _run_id
  - _run_type
  - _dq_errors
  - _dq_status
```

**Уникальна только 1 строка:** `primary_key` / `merge_keys` (и то = `business_primary_keys` из pipeline config).

**Вывод:** 21 файл × 18 строк = 378 строк, из которых 357 — копипаста.

#### P-002: DQ Pipeline Overrides Дублируют Entity Config (HIGH)

`pipelines/chembl/activity.yaml` содержит `dq_overrides` с 6 правилами, **5 из которых идентичны** правилам в `quality/entities/chembl/activity.yaml`.

Пример дубликата:
- Pipeline inline: `standard_value range [0, 1e9]`
- Entity DQ config: `standard_value range [0, 1e9]` (строки 22-27)

DQ loader дедуплицирует по `(field, type, severity)`, но поддержка двух мест — когнитивная нагрузка.

#### P-003: Filter Provider Level Почти Пуст (MEDIUM)

`filters/providers/chembl.yaml` содержит лишь:
```yaml
input_filter:
  batch_size: 1000
gold_filters:
  required_fields: []
  columns: {}
```

7 provider-файлов × 10 строк реального контента = 70 строк. Не оправдывает отдельный уровень.

#### P-004: Schema + Contract = Разделённая Ответственность (HIGH)

`schemas/chembl/activity.yaml` определяет:
- `content_hash.include/exclude` — то же что `contracts/.../hash_include/exclude`
- `column_groups` — семантическая группировка полей

`contracts/chembl/activity.yaml` определяет:
- `primary_key`, `merge_keys` — то же что `business_primary_keys` в pipeline
- `rename_map` — одинаков везде
- `hash_include/exclude` — дублирует schema

**Два файла описывают одну сущность с перекрытием.**

#### P-005: filter/_defaults.yaml — Пустой Шаблон (LOW)

77 строк, из которых 70 — комментарии. Всё = пустые списки и `enabled: false`. Полезен как документация, но не как runtime-конфиг.

#### P-006: Неконсистентные Параметры Между Pipeline Configs (MEDIUM)

| Параметр | chembl_activity | chembl_molecule | pubmed_publication | crossref_publication |
|----------|----------------|-----------------|--------------------|-----------------------|
| `batch_size` | 1000 (в pipeline) | - (default 100) | - (default 100) | - (default 100) |
| `loading_strategy` | - | - | full_scan_only | full_scan_only |
| `schema_file` | явный путь | явный путь | явный путь | явный путь |
| `partition_by` | - | molecule_type | - | - |
| `source` credentials | - | - | email + api_key | - |
| `dq_overrides` inline | 56 строк | - | - | - |

- `batch_size` дублируется: в pipeline config (1000) и в filter provider config (1000).
- `schema_file` указан явно у всех, хотя convention-defaults вычисляет его автоматически.
- `loading_strategy: full_scan_only` повторяется у 4/5 publication providers — можно вынести в base publication config.

#### P-007: Асимметрия Между Подсистемами (LOW)

| Подсистема | Файлов у chembl | Файлов у uniprot |
|------------|-----------------|-------------------|
| quality/entities | 14 | 3 (protein, idmapping, **target** — нет pipeline!) |
| filters/entities | 14 | 2 (protein, idmapping) |
| contracts | 14 | 2 |
| hash_policy | 1 (только activity) | 0 |

`quality/entities/uniprot/target.yaml` не имеет соответствующего pipeline config — осиротевший файл.

---

## 2. Текущая Архитектура Config Loading

### 2.1 Цепочка Разрешения (для стандартного pipeline)

```
load_pipeline_config(name)
  │
  ├─ READ _base.yaml ──────────┐
  ├─ READ {provider}/{entity}.yaml ─┤ deep_merge → unified dict
  │                                  │
  ├─ _apply_convention_defaults ─────┤ auto-set paths if missing
  │                                  │
  ├─ FilterConfigLoader.load_as_dict ┤ 4-level filter merge
  │   ├─ _defaults.yaml              │
  │   ├─ providers/{p}.yaml          │
  │   └─ entities/{p}/{e}.yaml       │
  │                                  │
  ├─ _load_column_groups_section ────┤ schema file → column_groups
  │   └─ schemas/{p}/{e}.yaml       │
  │                                  │
  ├─ _load_source_section ───────────┤ source file → provider config
  │   └─ sources/{p}.yaml           │
  │                                  │
  └─ PipelineYamlConfig.model_validate ─→ validated config

PipelineConfigLoader.resolve_dq_config(yaml_config)
  │
  ├─ DQConfigLoader.load(provider, entity)
  │   ├─ _defaults.yaml
  │   ├─ providers/{p}.yaml
  │   └─ entities/{p}/{e}.yaml
  │
  └─ merge with inline dq_overrides

yaml_config_to_domain(yaml_config, dq_config)
  └─ → PipelineConfig (domain object)
```

### 2.2 Config Loaders (в коде)

| Loader | Файл | Загружает | Кеш |
|--------|------|-----------|-----|
| `load_pipeline_config` | `infrastructure/config_loader.py` | `_base.yaml` + entity YAML + source + schema + filters | `@lru_cache(10)` |
| `DQConfigLoader` | `infrastructure/config/dq_config_loader.py` | `quality/` hierarchy (3 уровня) | internal dict |
| `FilterConfigLoader` | `infrastructure/config/filter_config_loader.py` | `filters/` hierarchy (3 уровня) | internal dict |
| `PipelineContractPolicyLoader` | `infrastructure/config/contract_policy_loader.py` | `contracts/pipelines/{p}/{e}.yaml` | `@lru_cache(128)` |
| `FieldGroupLoader` | `infrastructure/config/field_group_loader.py` | `schemas/composite/field_groups/` | none |
| `load_composite_config` | `composition/bootstrap/runtime/composite.py` | `pipelines/composite/{name}.yaml` | none |

### 2.3 Три Разных Реализации deep_merge

| Реализация | Файл | Логика list-слияния |
|------------|------|---------------------|
| `config_loader._deep_merge` | `config_loader.py:37` | scalar override (no list merge) |
| `BaseConfigLoader._deep_merge_base` | `base_config_loader.py:91` | configurable `list_concat_keys` (concat + dedup) |
| `DQConfigLoader._deep_merge` | `dq_config_loader.py` | `*_validations` dedup by composite key |

---

## 3. Целевая Архитектура

### 3.1 Принцип: Max 5 файлов, Min 2 Base

**Целевая формула:**

```
Standard Pipeline = 2 base + 1 provider + 1 entity = 4 файла
Composite Pipeline = 2 base + 1 provider + 1 entity + 1 composite = 5 файлов
```

### 3.2 Целевая Структура

```
configs/
├── base/
│   ├── pipeline.yaml          # BASE-1: pipeline execution defaults
│   └── quality.yaml           # BASE-2: DQ thresholds + common validations
│
├── providers/
│   ├── chembl.yaml            # PROVIDER: connection + DQ patterns + filter defaults + entity list
│   ├── crossref.yaml
│   ├── openalex.yaml
│   ├── pubchem.yaml
│   ├── pubmed.yaml
│   ├── semanticscholar.yaml
│   └── uniprot.yaml
│
├── entities/
│   ├── chembl/
│   │   ├── activity.yaml      # ENTITY: all-in-one (identity + schema + DQ + filters + contracts)
│   │   ├── assay.yaml
│   │   ├── molecule.yaml
│   │   └── ... (14 entities)
│   ├── crossref/
│   │   └── publication.yaml
│   ├── pubmed/
│   │   └── publication.yaml
│   └── ... (по 1 entity per provider)
│
├── composites/
│   ├── activity.yaml          # COMPOSITE: seed + enrichers + merge config
│   ├── publication.yaml
│   └── ... (5 composites)
│
├── _schema/                   # JSON Schema (kept as-is)
│   ├── pipeline.json
│   └── composite.json
│
└── enums/                     # Reference data (kept as-is)
    └── chembl.yaml
```

### 3.3 Что Куда Поглощается

| Текущий файл/dir | Целевое место | Действие |
|-------------------|---------------|----------|
| `pipelines/_base.yaml` | `base/pipeline.yaml` | Rename |
| `quality/_defaults.yaml` | `base/quality.yaml` | Rename |
| `filters/_defaults.yaml` | `base/pipeline.yaml` (section `filter_defaults`) | Merge into base |
| `sources/{p}.yaml` | `providers/{p}.yaml` (section `source`) | Merge |
| `quality/providers/{p}.yaml` | `providers/{p}.yaml` (section `quality`) | Merge |
| `filters/providers/{p}.yaml` | `providers/{p}.yaml` (section `filters`) | Merge |
| `pipelines/{p}/{e}.yaml` | `entities/{p}/{e}.yaml` (section `pipeline`) | Merge |
| `schemas/{p}/{e}.yaml` | `entities/{p}/{e}.yaml` (section `schema`) | Merge |
| `quality/entities/{p}/{e}.yaml` | `entities/{p}/{e}.yaml` (section `quality`) | Merge |
| `filters/entities/{p}/{e}.yaml` | `entities/{p}/{e}.yaml` (section `filters`) | Merge |
| `contracts/pipelines/{p}/{e}.yaml` | `entities/{p}/{e}.yaml` (section `contracts`) | Merge |
| `hash_policy/{p}/{e}.yaml` | `entities/{p}/{e}.yaml` (section `hash_policy`) | Merge |
| `pipelines/composite/{e}.yaml` | `composites/{e}.yaml` | Move |
| `naming_exceptions.yaml` | Keep as-is (utility, not per-pipeline) | No change |

### 3.4 Пример Целевых Файлов

#### BASE-1: `configs/base/pipeline.yaml`

```yaml
# Base Pipeline Configuration — Single Source of Truth
# All entity configs inherit these defaults.

version: "1.2.0"
technical_primary_key: "entity_id"
source: {}
transform:
  steps: []

sink:
  bronze:
    format: jsonl
    save_json: true
    save_metadata: true
    dq_report: { enabled: true }
    flat_structure: true
  silver:
    format: delta
    mode: merge
    on_schema_mismatch: evolve
    save_metadata: true
    dq_report: { enabled: true }
    csv_export: { enabled: true, delimiter: ",", header: true, encoding: "utf-8" }
    flat_structure: true
  gold:
    enabled: true
    format: delta
    mode: scd2
    scd_config:
      valid_from: _valid_from
      valid_to: _valid_to
      is_current: _is_current
      version: _version
    deterministic: true
    save_metadata: true
    dq_report: { enabled: true }
    csv_export: { enabled: true, delimiter: ",", header: true, encoding: "utf-8" }
    flat_structure: true

maintenance:
  auto_vacuum: false
  vacuum_retention_days: 7

input_filter:
  enabled: false
  batch_size: 100

# Filter structure defaults (previously filters/_defaults.yaml)
filter_defaults:
  silver_filters:
    required_fields: []
    columns: {}
    ranges: {}
    list_lengths: {}
    list_contains: {}
    exclude_if_present: []
  gold_filters:
    required_fields: []
    columns: {}
    ranges: {}
    list_lengths: {}
    list_contains: {}
    exclude_if_present: []

# Contract defaults (previously identical across ALL 21 entities)
contract_defaults:
  rename_map:
    run_id: _run_id
    run_type: _run_type
    source_batch_id: _source_batch_id
    ingestion_ts: _ingestion_ts
    source: _source
  hash_include: []
  hash_exclude:
    - _ingestion_ts
    - _run_id
    - _run_type
    - _dq_errors
    - _dq_status
```

#### BASE-2: `configs/base/quality.yaml`

```yaml
# Global DQ defaults for all BioETL pipelines

version: "1.0.0"

thresholds:
  soft_fail: 0.05
  hard_fail: 0.20

strict_validation: false
invalid_record_policy: quarantine

report:
  enabled: true
  format: json
  include_sample_failures: true
  sample_size: 10
  output_path: null

# Common validations applied to ALL entities
field_validations:
  - field: _content_hash
    type: required
    nullable: false
    error_message: "Content hash is required for deduplication"
  - field: _ingestion_ts
    type: pattern
    pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    nullable: false
    error_message: "Ingestion timestamp must be ISO 8601 format"

cross_field_validations: []
```

#### PROVIDER: `configs/providers/chembl.yaml`

```yaml
# ChEMBL Provider — all provider-level config in one place
version: "1.0.0"
provider: chembl

# --- Connection (previously sources/chembl.yaml) ---
source:
  batch_size: 10
  provider_config:
    provider: chembl
    base_url: https://www.ebi.ac.uk/chembl/api/data
    auth_type: public
    client:
      timeout_sec: 60.0
      max_retries: 3
    pagination:
      page_size: 1000
      id_batch_size: 20
      strategy: offset
      max_url_length: 2000
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
  rate_limit:
    requests_per_second: 3
    burst: 10
  health_check:
    endpoint: /chembl/api/data/status.json
    timeout: 5
  retry:
    use_retry_after: false

# --- DQ Rules (previously quality/providers/chembl.yaml) ---
quality:
  thresholds:
    hard_fail: 0.15   # Stricter than default
  field_validations:
    - field: molecule_id
      type: pattern
      pattern: '^CHEMBL\d+$'
      nullable: true
      error_message: "Invalid ChEMBL molecule ID format"
    - field: target_id
      type: pattern
      pattern: '^CHEMBL\d+$'
      nullable: true
      error_message: "Invalid ChEMBL target ID format"
    - field: assay_id
      type: pattern
      pattern: '^CHEMBL\d+$'
      nullable: true
    - field: publication_id
      type: pattern
      pattern: '^CHEMBL\d+$'
      nullable: true

# --- Filter Defaults (previously filters/providers/chembl.yaml) ---
filters:
  input_filter:
    batch_size: 1000

# --- Entity List ---
entities:
  - activity
  - assay
  - assay_parameters
  - cell_line
  - compound_record
  - molecule
  - protein_class
  - publication
  - publication_similarity
  - publication_term
  - subcellular_fraction
  - target
  - target_component
  - tissue
```

#### ENTITY: `configs/entities/chembl/molecule.yaml`

```yaml
# ChEMBL Molecule — unified entity config
version: "1.0.0"
provider: chembl
entity: molecule

# --- Pipeline (previously pipelines/chembl/molecule.yaml) ---
pipeline:
  name: chembl_molecule
  description: "Extract molecules/compounds from ChEMBL API"
  business_primary_keys: [molecule_id]
  sink:
    silver:
      partition_by: [molecule_type]

# --- Contracts (previously contracts/pipelines/chembl/molecule.yaml) ---
# Only entity-specific keys; rename_map and hash_exclude from base/pipeline.yaml
contracts:
  primary_key: [molecule_id]
  merge_keys: [molecule_id]

# --- Schema (previously schemas/chembl/molecule.yaml) ---
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
    - name: system
      fields: [entity_id, content_hash, _run_id, _run_type, _source_batch_id, _ingestion_ts, _index]
    - name: business
      fields:
        - molecule_id
        - pref_name
        - max_phase
        - molecule_type
        - ... # (полный список полей)
    - name: dq
      pattern: "^_dq_"
  silver:
    include_groups: [system, business, dq]
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups: [system, business]
    exclude_fields: [_dq_*, _source_batch_id, _index]
    alias_policy: canonical

# --- Quality (previously quality/entities/chembl/molecule.yaml) ---
quality:
  field_validations:
    - field: molecule_id
      type: required
      nullable: false
      error_message: "Molecule ID is required"
    - field: molecule_type
      type: enum
      allowed: [Small molecule, Protein, Antibody, Oligosaccharide, Enzyme, Cell, Unknown]
      nullable: true

# --- Filters (previously filters/entities/chembl/molecule.yaml) ---
filters:
  input_filter:
    enabled: true
    source_path: "data/input/molecule.csv"
    column_name: "molecule_chembl_id"
    filter_field: "molecule_id"
    batch_size: 20
  extraction_params:
    molecule_type: "Small molecule"
    structure_type: "MOL"
    inorganic_flag: 0
  silver_filters:
    columns:
      molecule_type: [Small molecule]
      structure_type: [MOL]
      inorganic_flag: ["0"]
    required_fields: [molecule_id]
  gold_filters:
    columns:
      molecule_type: [Small molecule]
      structure_type: [MOL]
      inorganic_flag: ["0"]
    required_fields: [molecule_id]
```

### 3.5 Сравнение: До и После

| Метрика | Текущее | Целевое | Δ |
|---------|---------|---------|---|
| Файлов на standard pipeline | 11 | **4** | -64% |
| Файлов на composite pipeline | 12 | **5** | -58% |
| Всего YAML файлов | 162 | **~40** | -75% |
| Базовых файлов | 3 (разрозненные) | **2** (консолидированные) | -33% |
| Provider файлов | 21 (3 dir × 7) | **7** (unified) | -67% |
| Дублированных строк (contracts) | 357 | **0** | -100% |
| Config loaders в коде | 6 | **3** | -50% |
| deep_merge реализаций | 3 | **1** | -67% |
| Dirs в configs/ | 9 | **5** | -44% |

---

## 4. План Рефакторинга

### 4.1 Фазы

#### Phase 0: Подготовка (без изменения поведения)

| ID | Задача | Файлы | Риск |
|----|--------|-------|------|
| RF-CFG-001 | Удалить `quality/entities/uniprot/target.yaml` (осиротевший) — **DONE** | 1 | LOW |
| RF-CFG-002 | Удалить дублирующий `dq_overrides` из `pipelines/chembl/activity.yaml` (5/6 правил = копия entity DQ) — **DONE** | 1 | LOW |
| RF-CFG-003 | Удалить явный `schema_file` из entity pipeline configs (convention-defaults вычислит) — **DONE (21 standard pipelines)** | 21 | LOW |
| RF-CFG-004 | ~~Выровнять `batch_size`~~ **SKIPPED**: pipeline `batch_size` (processing) ≠ filter `input_filter.batch_size` (API) — разные параметры | 0 | — |
| RF-CFG-005 | Добавить `loading_strategy: full_scan_only` как параметр в `_base.yaml` (default: null) — **DONE** | 1 | LOW |

#### Phase 1: Консолидация Base (2 base файла)

| ID | Задача | Файлы | Риск |
|----|--------|-------|------|
| RF-CFG-010 | Создать `configs/base/pipeline.yaml` из `pipelines/_base.yaml` + `filter_defaults` + `contract_defaults` — **DONE** | 2→1 | MEDIUM |
| RF-CFG-011 | Создать `configs/base/quality.yaml` (= rename `quality/_defaults.yaml`) — **DONE with fallback** (legacy file оставлен на transition) | 1→1 | LOW |
| RF-CFG-012 | Обновить `load_pipeline_config()` для чтения из `base/` — **DONE** | 1 | MEDIUM |
| RF-CFG-013 | Обновить `DQConfigLoader` для чтения из `base/` — **DONE** | 1 | MEDIUM |
| RF-CFG-014 | Удалить `filters/_defaults.yaml` — **DONE** | 1 | LOW |
| RF-CFG-015 | Добавить backward-compat fallback: если `base/pipeline.yaml` нет, читать `pipelines/_base.yaml` — **DONE** | 1 | LOW |

#### Phase 2: Консолидация Provider (1 файл per provider)

| ID | Задача | Файлы | Риск |
|----|--------|-------|------|
| RF-CFG-020 | Создать `configs/providers/{p}.yaml` = merge `sources/{p}` + `quality/providers/{p}` + `filters/providers/{p}` — **DONE** | 7×3→7 | MEDIUM |
| RF-CFG-021 | Обновить `load_source_config()` для чтения `providers/{p}.yaml` → section `source` — **DONE** | 1 | MEDIUM |
| RF-CFG-022 | Обновить `DQConfigLoader` для чтения `providers/{p}.yaml` → section `quality` — **DONE** | 1 | MEDIUM |
| RF-CFG-023 | Обновить `FilterConfigLoader` для чтения `providers/{p}.yaml` → section `filters` — **DONE** | 1 | MEDIUM |
| RF-CFG-024 | Backward-compat: если `providers/{p}.yaml` нет, fallback на `sources/{p}.yaml` — **DONE** | 1 | LOW |
| RF-CFG-025 | Удалить `sources/`, `quality/providers/`, `filters/providers/` | 21 | LOW |

#### Phase 3: Консолидация Entity (1 файл per entity)

| ID | Задача | Файлы | Риск |
|----|--------|-------|------|
| RF-CFG-030 | Создать `configs/entities/{p}/{e}.yaml` = merge 5 файлов в один — **DONE для standard pipelines (21/21), composite pending** | 5→1 (×26) | HIGH |
| RF-CFG-031 | Создать `UnifiedEntityConfigLoader` — один loader для entity | 1 new | HIGH |
| RF-CFG-032 | Рефакторить `load_pipeline_config()` для чтения unified entity — **DONE (unified-first + legacy fallback)** | 1 | HIGH |
| RF-CFG-033 | Удалить `PipelineContractPolicyLoader` (contracts в entity) — **IN PROGRESS** (loader оставлен для backward-compat) | 1 | MEDIUM |
| RF-CFG-034 | Удалить `FieldGroupLoader` для стандартных pipelines (schema в entity) — **PARTIAL** (standard path читает `schema` section) | 1 | MEDIUM |
| RF-CFG-035 | Удалить старые dirs: `pipelines/{p}/`, `schemas/{p}/`, `quality/entities/`, `filters/entities/`, `contracts/` | ~130 | MEDIUM |
| RF-CFG-036 | Перенести `pipelines/composite/*.yaml` → `composites/*.yaml` — **DONE** (`load_composite_config`: new-first + fallback) | 5 | LOW |
| RF-CFG-037 | Унифицировать 3 deep_merge в одну `config_merge()` утилиту — **DONE** (`src/bioetl/infrastructure/config_merge.py`) | 3→1 | MEDIUM |

#### Phase 4: Валидация и Документация

| ID | Задача | Файлы | Риск |
|----|--------|-------|------|
| RF-CFG-040 | Обновить JSON Schema (`_schema/pipeline.json`, `_schema/composite.json`) | 2 | MEDIUM |
| RF-CFG-041 | Обновить golden master тесты | ~10 | HIGH |
| RF-CFG-042 | Обновить `docs/04-reference/` — config reference docs | ~5 | LOW |
| RF-CFG-043 | Создать ADR-039: Config Unification (ADR-033 уже занят) | 1 | LOW |
| RF-CFG-044 | Обновить README в configs/ | 1 | LOW |

### 4.2 Порядок Выполнения

```
Phase 0 (cleanup)          → 0.5 дня  │ без рисков
Phase 1 (base consolidation) → 1 день  │ backward-compat fallback
Phase 2 (provider merge)     → 1 день  │ backward-compat fallback
Phase 3 (entity merge)       → 2-3 дня │ КЛЮЧЕВАЯ ФАЗА
Phase 4 (validation + docs)  → 1 день  │ golden master + ADR
                              ─────────
                              ~5-6 дней
```

### 4.3 Стратегия Миграции

1. **Backward compatibility** на каждой фазе: loader проверяет новый путь → fallback на старый
2. **Golden master tests** запускать после каждой фазы
3. **Phase 3 — incremental**: мигрировать по 1 provider за раз (chembl → crossref → ...)
4. **deprecation warnings** при чтении из старых путей: `logger.warn("Deprecated config path")`
5. **Удаление старых файлов** — отдельный PR после полной миграции

### 4.4 Ключевые Решения (для обсуждения)

| # | Вопрос | Рекомендация |
|---|--------|--------------|
| D-1 | Нужен ли backward-compat period? | Да, 1 релиз (loaders ищут оба пути) |
| D-2 | Один deep_merge или специализированные? | Один с параметром `list_strategy` |
| D-3 | Формат entity YAML — flat или sectioned? | Sectioned (`pipeline:`, `schema:`, `quality:`, `filters:`, `contracts:`) |
| D-4 | Оставить `configs/enums/` отдельно? | Да, это reference data, не per-pipeline |
| D-5 | Composite configs — отдельный dir или в entities? | Отдельный `composites/` — другая структура |

---

## 5. Параметры Для Выравнивания (Phase 0)

### 5.1 `schema_file` — можно удалить из entity configs

Все 21 standard pipeline config содержали явный `schema_file: ../../schemas/{p}/{e}.yaml`.
Код `_apply_convention_defaults` уже вычисляет этот путь автоматически.
**Статус:** выполнено для standard pipelines.

### 5.2 `batch_size` — дублируется в 2 местах

- `pipelines/chembl/activity.yaml`: `batch_size: 1000`
- `filters/providers/chembl.yaml`: `input_filter.batch_size: 1000`

Параметры выглядят похоже, но имеют разный смысл:
- `pipeline.batch_size` = размер обработки/записи batch в pipeline execution.
- `input_filter.batch_size` = размер API/input batch в filter extraction.
**Действие:** не удалять `pipeline.batch_size`; оставить RF-CFG-004 в статусе **SKIPPED**.

### 5.3 `dq_overrides` — дубликаты с entity DQ config

`chembl_activity` — единственный pipeline с inline `dq_overrides`.
Ранее 5 из 6 правил были идентичны `quality/entities/chembl/activity.yaml`; дубли уже удалены.
**Текущий остаток (валидный):** только narrowing overrides для `standard_type` и `standard_units`.

### 5.4 `loading_strategy` — добавить в base

4 pipeline configs содержат `loading_strategy: full_scan_only`.
Не определено в `_base.yaml`.
**Действие:** добавить `loading_strategy: null` в `_base.yaml` (null = default incremental).

---

## Приложение A: Полная Карта Файлов (Текущее → Целевое)

```
ТЕКУЩЕЕ (162 YAML)                         ЦЕЛЕВОЕ (~40 YAML)
═══════════════════                         ═══════════════════

pipelines/_base.yaml ──────────────────┐
filters/_defaults.yaml ────────────────┼──→ base/pipeline.yaml
contracts (21 файлов, rename_map) ─────┘

quality/_defaults.yaml ──────────────────→ base/quality.yaml

sources/chembl.yaml ───────────────────┐
quality/providers/chembl.yaml ─────────┼──→ providers/chembl.yaml
filters/providers/chembl.yaml ─────────┘
  (×7 providers)

pipelines/chembl/activity.yaml ────────┐
schemas/chembl/activity.yaml ──────────┤
quality/entities/chembl/activity.yaml ─┼──→ entities/chembl/activity.yaml
filters/entities/chembl/activity.yaml ─┤
contracts/pipelines/chembl/activity.yaml┘
  (×26 entities)

pipelines/composite/*.yaml ───────────→ composites/*.yaml (5)

_schema/*.json ───────────────────────→ _schema/*.json (2, kept)
enums/chembl.yaml ────────────────────→ enums/chembl.yaml (kept)
naming_exceptions.yaml ───────────────→ naming_exceptions.yaml (kept)
hash_policy/chembl/activity.yaml ─────→ entities/chembl/activity.yaml (section hash_policy)
```
