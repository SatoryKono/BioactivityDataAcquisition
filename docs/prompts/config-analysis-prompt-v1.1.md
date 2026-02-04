# BioETL: Промпт для Анализа и Унификации Конфигурационных Файлов

**Версия**: 1.1
**Дата**: 2026-02-04
**Режим**: ANALYSIS
**Совместимость**: BioETL v2.1+, _base.yaml v2.1.0

---

## 1. ЦЕЛЬ ЗАДАЧИ

Выполнить систематический анализ всех конфигурационных файлов проекта BioETL для:
1. Выявления расхождений в наборах параметров между разными пайплайнами
2. Идентификации отсутствующих обязательных параметров
3. Обнаружения неконсистентных значений по умолчанию
4. Проверки соответствия convention-based path resolution (ADR-029)
5. Подготовки плана унификации с учётом ADR-014, ADR-025, ADR-026, ADR-027, ADR-028, ADR-029

---

## 2. АРХИТЕКТУРНЫЙ КОНТЕКСТ

### 2.1 Ключевые ADR (Architecture Decision Records)

**Расположение**: `docs/02-architecture/decisions/`

| ADR | Название | Влияние на анализ |
|-----|----------|-------------------|
| **ADR-014** | Deterministic Writes | `sort_by` MUST присутствовать для Silver и Gold |
| **ADR-025** | Pipeline Config Unification | Единый `_base.yaml`, иерархия наследования |
| **ADR-026** | Composite Pipeline Pattern | Отдельная схема для composite pipelines |
| **ADR-027** | DQ Rules Externalization | Иерархия `_defaults → provider → entity` |
| **ADR-028** | Filter Rules Externalization | Аналогичная иерархия для filters |
| **ADR-029** | Convention-based Paths | Автовычисление путей из `provider`/`entity_type` |
| **ADR-030** | Publication Pagination Strategy | `force_full_scan` для publication entities |
| **ADR-031** | Loading Strategy Formalization | `loading_strategy: full_scan_only` |

### 2.2 Convention-Based Path Resolution (КРИТИЧНО!)

Согласно ADR-029, конфиг-лоадер автоматически вычисляет параметры из `provider` и `entity_type`:

```yaml
# Если в конфиге указано:
provider: chembl
entity_type: activity
primary_keys: ["activity_id"]

# То автоматически вычисляется:
source_file:        ../../sources/chembl.yaml
dq_config_file:     ../../dq/entities/chembl/activity.yaml
filter_config_file: ../../filter/entities/chembl/activity.yaml

sink.bronze.path:   data/output/bronze/chembl/activity
sink.silver.path:   data/output/silver/chembl/activity
sink.gold.path:     data/output/gold/chembl/activity

sink.silver.primary_key:      ["activity_id"]  # ← из primary_keys
sink.silver.sort_by.columns:  ["activity_id"]  # ← из primary_keys
sink.gold.sort_by.columns:    ["activity_id"]  # ← из primary_keys
```

**ВАЖНО**: При анализе различать:
- **Explicit override** — параметр указан явно в конфиге
- **Convention-derived** — параметр вычисляется автоматически

---

## 3. SCOPE АНАЛИЗА

### 3.1 Структура директории configs/

```
configs/
├── pipelines/                    # Pipeline конфигурации
│   ├── _base.yaml                # Unified Base Schema v2.1.0
│   ├── _schema.json              # JSON Schema для entity configs
│   ├── _composite_schema.json    # JSON Schema для composite configs
│   ├── chembl/                   # 12 entity configs
│   ├── pubchem/                  # 1 entity config
│   ├── uniprot/                  # 2 entity configs
│   ├── pubmed/                   # 1 entity config
│   ├── crossref/                 # 1 entity config
│   ├── openalex/                 # 1 entity config
│   ├── semanticscholar/          # 1 entity config
│   └── composite/                # 4 composite configs
│
├── dq/                           # Data Quality правила
│   ├── _defaults.yaml            # Global DQ defaults (Level 1)
│   ├── README.md                 # Документация DQ
│   ├── providers/                # Provider-level DQ (Level 2)
│   │   └── {provider}.yaml       # 7 файлов
│   └── entities/                 # Entity-level DQ (Level 3)
│       └── {provider}/
│           └── {entity}.yaml     # ~20 файлов
│
├── filter/                       # Filter правила
│   ├── _defaults.yaml            # Global filter defaults (Level 1)
│   ├── README.md                 # Документация filters
│   ├── providers/                # Provider-level filters (Level 2)
│   │   └── {provider}.yaml       # 7 файлов
│   └── entities/                 # Entity-level filters (Level 3)
│       └── {provider}/
│           └── {entity}.yaml     # ~27 файлов
│
├── sources/                      # Source configurations
│   └── {provider}.yaml           # 7 файлов
│
├── data_schema/                  # Column definitions per layer
│   ├── composite/                # 2 файла
│   ├── chembl/                   # 13 файлов
│   ├── {other_providers}/        # 1 файл каждый
│   └── examples/                 # Reference examples
│
└── naming_exceptions.yaml        # Исключения из naming conventions
```

### 3.2 Полный список файлов для анализа

**Pipeline configs (24 файла):**

| Provider | Entity | Тип | Файл |
|----------|--------|-----|------|
| (base) | - | schema | `_base.yaml`, `_schema.json`, `_composite_schema.json` |
| chembl | activity | entity | `chembl/activity.yaml` |
| chembl | assay | entity | `chembl/assay.yaml` |
| chembl | assay_parameters | entity | `chembl/assay_parameters.yaml` |
| chembl | cell_line | entity | `chembl/cell_line.yaml` |
| chembl | compound_record | entity | `chembl/compound_record.yaml` |
| chembl | molecule | entity | `chembl/molecule.yaml` |
| chembl | protein_class | entity | `chembl/protein_class.yaml` |
| chembl | publication | entity | `chembl/publication.yaml` |
| chembl | publication_similarity | entity | `chembl/publication_similarity.yaml` |
| chembl | publication_term | entity | `chembl/publication_term.yaml` |
| chembl | target | entity | `chembl/target.yaml` |
| chembl | target_component | entity | `chembl/target_component.yaml` |
| pubchem | compound | entity | `pubchem/compound.yaml` |
| uniprot | protein | entity | `uniprot/protein.yaml` |
| uniprot | idmapping | entity | `uniprot/idmapping.yaml` |
| pubmed | publication | entity | `pubmed/publication.yaml` |
| crossref | publication | entity | `crossref/publication.yaml` |
| openalex | publication | entity | `openalex/publication.yaml` |
| semanticscholar | publication | entity | `semanticscholar/publication.yaml` |
| composite | activity | composite | `composite/activity.yaml` |
| composite | molecule | composite | `composite/molecule.yaml` |
| composite | publication | composite | `composite/publication.yaml` |
| composite | target | composite | `composite/target.yaml` |

**DQ configs (~30 файлов):**
- `configs/dq/_defaults.yaml`
- `configs/dq/providers/*.yaml` (7 файлов)
- `configs/dq/entities/{provider}/{entity}.yaml` (~20 файлов)

**Filter configs (~35 файлов):**
- `configs/filter/_defaults.yaml`
- `configs/filter/providers/*.yaml` (7 файлов)
- `configs/filter/entities/{provider}/{entity}.yaml` (~27 файлов)

**Source configs (7 файлов):**
- `configs/sources/{chembl,pubchem,uniprot,pubmed,crossref,openalex,semanticscholar}.yaml`

**Data schema configs (~23 файла):**
- `configs/data_schema/{provider}/{entity}.yaml`

---

## 4. ПАРАМЕТРЫ ДЛЯ АНАЛИЗА

### 4.1 Pipeline Config — REQUIRED (из _schema.json)

| Параметр | Тип | Паттерн/Значения | Описание |
|----------|-----|------------------|----------|
| `pipeline_name` | string | `^[a-z]+_[a-z_]+$` | Уникальный идентификатор |
| `provider` | enum | chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar | Провайдер данных |
| `entity_type` | string | - | Тип сущности |
| `version` | string | `^\d+\.\d+\.\d+$` | Семантическая версия |
| `primary_keys` | list[str] | minItems: 1 | Business keys |
| `silver_table` | string | - | Имя таблицы Silver |
| `gold_table` | string | - | Имя таблицы Gold |

### 4.2 Pipeline Config — OPTIONAL (с auto-propagation)

| Параметр | Тип | Default / Auto-computed | Описание |
|----------|-----|-------------------------|----------|
| `description` | string | null | Human-readable описание |
| `force_full_scan` | bool | false | Отключить checkpoint resume (ADR-030) |
| `loading_strategy` | enum | "incremental" | incremental \| full_scan_only (ADR-031) |
| `batch_size` | int | provider default | Override batch size |
| `checkpoint_interval` | int | provider default | Records between checkpoints |
| `source_file` | string | `../../sources/{provider}.yaml` | Path to source config |
| `dq_config_file` | string | `../../dq/entities/{provider}/{entity_type}.yaml` | Path to DQ config |
| `filter_config_file` | string | `../../filter/entities/{provider}/{entity_type}.yaml` | Path to filter config |
| `data_schema_file` | string | null | Path to data schema (layer columns) |
| `column_groups_file` | string | null | Legacy; prefer data_schema_file |

### 4.3 Sink Configuration (ADR-029 auto-computed)

| Параметр | Тип | Auto-computed from | Описание |
|----------|-----|-------------------|----------|
| `sink.bronze.path` | string | `data/output/bronze/{provider}/{entity_type}` | Bronze output |
| `sink.silver.path` | string | `data/output/silver/{provider}/{entity_type}` | Silver output |
| `sink.silver.primary_key` | list[str] | `{primary_keys}` | Merge key |
| `sink.silver.sort_by.columns` | list[str] | `{primary_keys}` | ADR-014 |
| `sink.silver.sort_by.ascending` | bool | true | Direction |
| `sink.gold.path` | string | `data/output/gold/{provider}/{entity_type}` | Gold output |
| `sink.gold.sort_by.columns` | list[str] | `{primary_keys}` | ADR-014 |
| `sink.gold.sort_by.ascending` | bool | true | Direction |

### 4.4 DQ Config Parameters (`configs/dq/`)

**_defaults.yaml — глобальные defaults:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `version` | string | "1.0.0" | Schema version |
| `thresholds.soft_fail` | float | 0.05 | Warning threshold (5%) |
| `thresholds.hard_fail` | float | 0.20 | Fail threshold (20%) |
| `strict_validation` | bool | false | Feature flag |
| `invalid_record_policy` | enum | "quarantine" | quarantine \| skip \| fail |
| `report.enabled` | bool | true | DQ report generation |
| `report.format` | enum | "json" | json \| yaml \| csv |
| `report.include_sample_failures` | bool | true | Include examples |
| `report.sample_size` | int | 10 | Max failures to show |
| `common_field_validations` | list | [_content_hash, _ingestion_ts] | Global validations |

**Entity-level additions:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `field_validations` | list | Field-level rules (range, pattern, enum, custom) |
| `cross_field_validations` | list | Multi-field constraints |
| `conditional_validations` | list | Condition-based rules |

### 4.5 Filter Config Parameters (`configs/filter/`)

**_defaults.yaml:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `version` | string | "1.0.0" | Schema version |
| `input_filter.enabled` | bool | false | Enable input filtering |
| `input_filter.batch_size` | int | 100 | IDs per API request |
| `gold_filters.required_fields` | list[str] | [] | Non-null fields |
| `gold_filters.columns` | dict | {} | Value inclusion filters |
| `gold_filters.ranges` | dict | {} | Numeric range filters |
| `gold_filters.list_lengths` | dict | {} | List size constraints |
| `gold_filters.list_contains` | dict | {} | List content filters |
| `gold_filters.exclude_if_present` | list[str] | [] | Exclusion fields |

### 4.6 Source Config Parameters (`configs/sources/`)

| Параметр | Тип | Описание |
|----------|-----|----------|
| `source.type` | enum | api \| file |
| `source.load_strategy` | enum | full \| incremental |
| `source.batch_size` | int | Provider batch size |
| `source.provider_config.base_url` | string | API endpoint |
| `source.provider_config.auth_type` | string | public \| api_key \| oauth |
| `source.provider_config.client.timeout_sec` | float | Request timeout |
| `source.provider_config.client.max_retries` | int | Retry count |
| `source.rate_limit.requests_per_second` | float | RPS limit |
| `source.rate_limit.burst` | int | Burst capacity |
| `source.circuit_breaker.failure_threshold` | int | Failures before open |
| `source.circuit_breaker.recovery_timeout` | int | Recovery time (sec) |
| `source.health_check.endpoint` | string | Health probe URL |
| `source.retry.use_retry_after` | bool | Honor Retry-After header |

---

## 5. ИНСТРУКЦИИ ПО АНАЛИЗУ

### 5.1 Шаг 1: Инвентаризация файлов

```bash
# Подсчёт файлов по категориям
find configs/pipelines -name "*.yaml" | wc -l        # Expected: 24+
find configs/dq -name "*.yaml" | wc -l               # Expected: ~28
find configs/filter -name "*.yaml" | wc -l           # Expected: ~35
find configs/sources -name "*.yaml" | wc -l          # Expected: 7
find configs/data_schema -name "*.yaml" | wc -l      # Expected: ~23
```

### 5.2 Шаг 2: Валидация против JSON Schema

```bash
# Валидация entity configs
for f in configs/pipelines/*/*.yaml; do
  if [[ ! "$f" =~ "composite" ]]; then
    jsonschema -i "$f" configs/pipelines/_schema.json
  fi
done

# Валидация composite configs
for f in configs/pipelines/composite/*.yaml; do
  jsonschema -i "$f" configs/pipelines/_composite_schema.json
done
```

### 5.3 Шаг 3: Извлечение параметров

Для каждого конфига извлечь:
1. **Explicit parameters** — все ключи, указанные в файле
2. **Convention-derived** — параметры, которые должны вычисляться автоматически
3. **Override detection** — где explicit != convention (требует justification)
4. **Типы и значения** — для сравнения с defaults

### 5.4 Шаг 4: Матрица сравнения

```
| Parameter Path           | Source | chembl/activity | chembl/assay | pubchem/compound |
|--------------------------|--------|-----------------|--------------|------------------|
| pipeline_name            | req    | chembl_activity | chembl_assay | pubchem_compound |
| primary_keys             | req    | [activity_id]   | [assay_chembl_id] | [cid]       |
| sink.silver.sort_by      | auto   | (convention)    | (convention) | (convention)     |
| dq_rules.thresholds.soft_fail | dq  | (default)      | 0.10 (override) | (default)   |
```

### 5.5 Шаг 5: Классификация расхождений

| Категория | Severity | Описание |
|-----------|----------|----------|
| `MISSING_REQUIRED` | HIGH | Обязательный параметр отсутствует |
| `CONVENTION_VIOLATION` | HIGH | Параметр противоречит ADR-029 без justification |
| `INCONSISTENT_DEFAULT` | MEDIUM | Разные значения для одного параметра без обоснования |
| `REDUNDANT_EXPLICIT` | LOW | Explicit override == convention (лишний код) |
| `UNDOCUMENTED_OVERRIDE` | MEDIUM | Override без комментария с обоснованием |
| `DEPRECATED_PARAMETER` | LOW | Использование legacy параметра (column_groups_file) |
| `SCHEMA_DRIFT` | HIGH | Параметр не описан в _schema.json |

---

## 6. ФОРМАТ ВЫХОДНОГО ОТЧЁТА

### 6.1 Summary Section

```yaml
analysis_metadata:
  generated_at: "2026-02-04T12:00:00Z"
  prompt_version: "1.1"
  base_yaml_version: "2.1.0"

inventory:
  pipelines:
    entity_configs: 20
    composite_configs: 4
    schema_files: 3
  dq:
    defaults: 1
    provider_configs: 7
    entity_configs: 20
  filter:
    defaults: 1
    provider_configs: 7
    entity_configs: 27
  sources: 7
  data_schema: 23
  total_yaml_files: 118

coverage:
  pipelines:
    total: 24
    valid_against_schema: 24
    convention_compliant: 20
    with_overrides: 4
  dq:
    total: 28
    aligned_with_defaults: 25
    with_threshold_overrides: 3
```

### 6.2 Issues Section

```yaml
issues:
  - id: CFG-001
    severity: HIGH
    category: MISSING_REQUIRED
    file: configs/pipelines/chembl/new_entity.yaml
    parameter: primary_keys
    expected: "list[str] with minItems: 1"
    actual: null
    adr_reference: ADR-025
    remediation: "Add primary_keys: ['<entity>_id']"

  - id: CFG-002
    severity: MEDIUM
    category: INCONSISTENT_DEFAULT
    files:
      - configs/dq/entities/chembl/activity.yaml
      - configs/dq/entities/chembl/molecule.yaml
    parameter: thresholds.soft_fail
    values: [0.05, 0.10]
    default: 0.05
    recommendation: "Документировать причину override 0.10 в molecule.yaml"

  - id: CFG-003
    severity: LOW
    category: REDUNDANT_EXPLICIT
    file: configs/pipelines/chembl/activity.yaml
    parameter: sink.silver.path
    explicit_value: "data/output/silver/chembl/activity"
    convention_value: "data/output/silver/chembl/activity"
    recommendation: "Удалить explicit sink.silver.path — convention-based достаточно"
```

### 6.3 Convention Compliance Matrix

```csv
pipeline,provider,entity_type,source_file,dq_config_file,filter_config_file,bronze_path,silver_path,gold_path,compliance
chembl_activity,chembl,activity,convention,convention,convention,convention,convention,convention,FULL
chembl_molecule,chembl,molecule,explicit,convention,convention,convention,convention,convention,PARTIAL
pubmed_publication,pubmed,publication,convention,convention,convention,explicit,explicit,explicit,OVERRIDE
```

### 6.4 Recommendations Section

```yaml
recommendations:
  - priority: P1
    category: schema_compliance
    description: "Добавить primary_keys в 2 конфига"
    affected_files:
      - configs/pipelines/...
    adr_reference: ADR-025
    effort: "15 min"

  - priority: P2
    category: convention_adoption
    description: "Удалить redundant explicit paths из 5 конфигов"
    rationale: "ADR-029 auto-computes идентичные значения"
    effort: "10 min"

  - priority: P3
    category: documentation
    description: "Добавить justification comments для 3 threshold overrides"
    affected_files: [...]
    effort: "5 min"
```

---

## 7. КРИТЕРИИ КАЧЕСТВА АНАЛИЗА

### 7.1 Полнота

- [ ] Все 24 pipeline configs обработаны
- [ ] Все DQ configs (defaults + providers + entities) обработаны
- [ ] Все Filter configs обработаны
- [ ] Все Source configs обработаны
- [ ] Data schema configs учтены (если referenced)
- [ ] `_base.yaml` defaults учтены при сравнении
- [ ] ADR-029 convention rules применены

### 7.2 Точность

- [ ] Каждая issue имеет точный `файл:параметр`
- [ ] Типы значений определены корректно
- [ ] Convention vs explicit различены
- [ ] Сравнение с _schema.json выполнено
- [ ] Merge priority (defaults → provider → entity → inline) учтён

### 7.3 Actionability

- [ ] Каждая issue имеет `remediation`
- [ ] Рекомендации приоритизированы (P1/P2/P3)
- [ ] ADR references указаны
- [ ] Effort оценён

---

## 8. MERGE PRIORITY REFERENCE

### DQ Config Merge (ADR-027)

```
Priority (lowest → highest):
1. configs/dq/_defaults.yaml
2. configs/dq/providers/{provider}.yaml
3. configs/dq/entities/{provider}/{entity}.yaml
4. Inline dq_rules in pipeline config
```

**Merge rules:**
- Scalars: later wins
- `*_validations` lists: concatenate with dedup by `field`/`name`
- Nested dicts: recursive merge

### Filter Config Merge (ADR-028)

```
Priority (lowest → highest):
1. configs/filter/_defaults.yaml
2. configs/filter/providers/{provider}.yaml
3. configs/filter/entities/{provider}/{entity}.yaml
4. Inline input_filter/gold_filters in pipeline config
```

**Merge rules:**
- Scalars: later wins
- `required_fields`, `exclude_if_present`: concatenate with dedup
- Nested dicts (`columns`, `ranges`, etc.): recursive merge

---

## 9. ОЖИДАЕМЫЕ АРТЕФАКТЫ

1. **config_analysis_report.yaml** — Полный отчёт в YAML
2. **config_comparison_matrix.csv** — Матрица сравнения (Excel-совместимая)
3. **convention_compliance.csv** — Compliance с ADR-029
4. **config_issues.md** — Human-readable список проблем
5. **unification_plan.md** — План действий по унификации

---

## 10. VERIFICATION CHECKLIST

После анализа проверить:

- [ ] Все 24 pipeline configs (20 entity + 4 composite) обработаны
- [ ] JSON Schema validation пройдена для всех configs
- [ ] Convention vs explicit paths различены (ADR-029)
- [ ] DQ merge priority учтён (ADR-027)
- [ ] Filter merge priority учтён (ADR-028)
- [ ] sort_by присутствует или auto-computed (ADR-014)
- [ ] Recommendations приоритизированы (P1/P2/P3)
- [ ] Каждый override имеет documented justification

---

## TL;DR

| Metric | Value |
|--------|-------|
| **Total YAML files** | ~118 |
| **Pipeline configs** | 24 (20 entity + 4 composite) |
| **DQ configs** | ~28 (1 defaults + 7 providers + 20 entities) |
| **Filter configs** | ~35 (1 defaults + 7 providers + 27 entities) |
| **Source configs** | 7 |
| **Data schema** | ~23 |
| **Key ADRs** | ADR-014, ADR-025, ADR-026, ADR-027, ADR-028, ADR-029, ADR-030, ADR-031 |
| **Convention-based params** | paths, primary_key, sort_by.columns |
| **Merge hierarchy** | defaults → provider → entity → inline |

---

## CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-03 | Initial version |
| 1.1 | 2026-02-04 | Fixed pipeline count (24 not 20), added ADR-029 convention-based analysis, corrected DQ parameter names (thresholds.soft_fail), added composite pipelines (4), added data_schema/, corrected ADR path, removed deprecated quarantine_enabled |
