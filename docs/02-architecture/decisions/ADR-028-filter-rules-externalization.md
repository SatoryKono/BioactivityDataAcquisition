# ADR-028: Filter Rules Externalization

**Status:** Accepted
**Date:** 2026-02-09
**Decision makers:** @BioETL-Team

## Context

Filter configurations (`input_filter` and `gold_filters`) were embedded directly in pipeline YAML configuration files (`configs/pipelines/{provider}/{entity}.yaml`). This caused several problems:

1. **Duplication**: Same filter patterns repeated across pipelines (e.g., batch_size defaults)
2. **Maintenance burden**: Changing global filter policies required editing multiple files
3. **No reusability**: Impossible to share filter patterns across providers/entities
4. **SRP violation**: Pipeline config mixed orchestration and filtering concerns

Example of duplication:
```yaml
# configs/pipelines/chembl/activity.yaml
input_filter:
  batch_size: 20

# configs/pipelines/chembl/molecule.yaml
input_filter:
  batch_size: 20  # Duplicated provider default
```

This pattern follows ADR-027 (DQ Rules Externalization) to create a consistent hierarchical configuration system.

## Decision

Extract filter rules into a hierarchical configuration structure:

```
configs/filters/
├── _defaults.yaml           # Global defaults (Level 1)
├── README.md                # Documentation
├── providers/
│   └── {provider}.yaml      # Provider overrides (Level 2)
└── entities/
    └── {provider}/
        └── {entity}.yaml    # Entity-specific rules (Level 3)
```

**Merge priority** (later wins for scalars, special handling for collections):
1. `_defaults.yaml`
2. `providers/{provider}.yaml`
3. `entities/{provider}/{entity}.yaml`
4. Inline `filter_rules` in pipeline config (for exceptional cases)

Pipeline configs reference filter config via `filter_config_file`:
```yaml
pipeline_name: chembl_activity
filter_config_file: ../../filter/entities/chembl/activity.yaml
```

### Implementation Components

1. **Pydantic schemas**: `src/bioetl/infrastructure/schemas/filter_config.py`
   - `InputFilterFileConfig`: Input filter configuration
   - `GoldFiltersFileConfig`: Gold layer filter configuration
   - `FilterConfigFile`: Complete schema with to_domain() conversion

2. **Configuration loader**: `src/bioetl/infrastructure/config/filter_config_loader.py`
   - `FilterConfigLoader.load(provider, entity, inline_overrides)`: Merges configs
   - Thread-safe caching for performance
   - Deep merge with list deduplication for required_fields/exclude_if_present

3. **Config files**: `configs/filters/`
   - `_defaults.yaml`: Global defaults (batch_size=100)
   - `providers/{provider}.yaml`: Provider-specific settings (e.g., ChEMBL batch_size=20)
   - `entities/{provider}/{entity}.yaml`: Entity-specific rules

4. **Pipeline schema update**: `src/bioetl/infrastructure/schemas/pipeline_config.py`
   - Added `filter_config_file` field to `PipelineYamlConfig`
   - Added `filter_rules` field for inline overrides
   - Legacy `input_filter`/`gold_filters` fields retained for backward compatibility

## Consequences

### Positive

- **DRY**: Provider-level defaults (e.g., ChEMBL batch_size=20) defined once
- **Separation of Concerns**: Pipeline config focuses on orchestration
- **Reusability**: Provider-level filters shared across entities
- **Flexibility**: Entity-specific rules without affecting others
- **Backward compatible**: Inline `input_filter`/`gold_filters` still supported
- **Type safety**: Pydantic validation catches config errors early
- **Performance**: Caching prevents repeated file reads
- **Consistency**: Follows same pattern as DQ configuration (ADR-027)

### Negative

- **More files**: Additional 20+ config files (mitigated by clear structure)
- **Indirection**: Must look at multiple files to understand full config
- **Merge complexity**: Need to understand merge behavior

### Neutral

- Migration effort: Existing pipelines work without changes during transition
- Tooling: Config validation scripts provided

## Merge Rules

| Data Type | Behavior | Example |
|-----------|----------|---------|
| Scalars | Override (later wins) | `batch_size: 50` replaces `100` |
| `required_fields` | Concatenate with dedup | Entity fields added to provider |
| `exclude_if_present` | Concatenate with dedup | Entity exclusions added to provider |
| Nested dicts (`columns`, `ranges`, etc.) | Recursive merge | Entity columns merged with provider |
| Other lists | Override (later wins) | `columns.field: [A, B]` replaces `[X, Y]` |

## Filter Types

### Input Filter Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `enabled` | bool | Enable/disable input filtering |
| `source_path` | str | Path to CSV file with filter IDs |
| `column_name` | str | CSV column with primary IDs |
| `filter_field` | str | API field to filter by |
| `batch_size` | int | IDs per API request (1-1000) |
| `fallback_column` | str | Optional fallback search field |

### Gold Filter Types

| Filter | Parameters | Description |
|--------|------------|-------------|
| `required_fields` | list[str] | Fields must be non-null |
| `columns` | dict[str, list] | Value inclusion list |
| `ranges` | dict[str, Range] | Numeric bounds |
| `list_lengths` | dict[str, MinMax] | List size constraints |
| `list_contains` | dict[str, Contains] | List content filter |
| `exclude_if_present` | list[str] | Exclude if field has value |

### §3. Extraction-Level Filtering (extraction_params)

#### Назначение

Серверные query parameters для API-провайдеров, применяемые на этапе
Bronze extraction. Сокращают объём трафика — API возвращает только
релевантные записи вместо полного датасета.

#### Область применения

- Только Bronze extract, не влияет на transform/load
- Provider-specific синтаксис (ChEMBL: `__in`, `__isnull`, `__gt` и др.)
- Параметры НЕ влияют на content_hash (ADR-014)

#### Конфигурация

Размещается в `configs/filters/` hierarchy как секция `extraction_params`:

```yaml
# configs/filters/entities/chembl/activity.yaml
extraction_params:
  standard_type__in: "IC50,Ki"
  standard_units: "nM"
  standard_relation: "="
  assay_type__in: "B,F"
  potential_duplicate: 0
  data_validity_comment__isnull: true
  pchembl_value__isnull: false
  standard_flag: 1
```

#### Merge order

`configs/filters/_defaults.yaml` → `providers/{provider}.yaml`
→ `entities/{provider}/{entity}.yaml`

Entity-level `extraction_params` полностью заменяет provider-level
(не merge отдельных ключей, а full override секции).

#### Взаимодействие с input_filter

- `extraction_params`: фильтрует по СВОЙСТВАМ записей (статические, из YAML)
- `input_filter`: фильтрует по ID (динамические, из CSV)
- Применяются совместно (AND семантика в API запросе)
- При пересечении ключей — WARNING, `input_filter` override

#### Взаимодействие с gold_filters

- `extraction_params`: pre-extract (API-side)
- `gold_filters`: post-load (client-side, Silver→Gold)
- Не конфликтуют — разные точки применения

#### Ограничения

- НЕТ CLI override (детерминизм, ADR-014)
- MUST логироваться в `SourceMetadata.query_string`
- Provider-specific: не все провайдеры поддерживают серверную фильтрацию

#### Domain representation

`ExtractionParams` frozen dataclass в `domain/models/filter.py`

### Filter Type Comparison

| Aspect | `input_filter` (§1) | `gold_filters` (§2) | `extraction_params` (§3) |
|--------|---------------------|----------------------|--------------------------|
| Stage | Bronze extract | Silver→Gold transform | Bronze extract |
| Side | Client-side (ID batching) | Client-side (DataFrame) | Server-side (API query) |
| Source | CSV file (dynamic) | YAML (static) | YAML (static) |
| Filters by | Record IDs | Field values, ranges, nulls | Record properties |
| Merge behavior | Recursive merge | Recursive merge | Full override (section-level) |
| CLI override | No (ADR-014) | No (ADR-014) | No (ADR-014) |
| Affects content_hash | No (ADR-014) | No | No (ADR-014) |
| Provider-specific | No (generic ID filter) | No (generic DataFrame filter) | Yes (API syntax) |

## Alternatives Considered

### 1. Keep Inline Only
Keep all filter configs inline in pipeline files. Rejected because:
- Duplication of provider defaults
- No reusability across entities
- Inconsistent with DQ configuration approach

### 2. Merge with DQ Config
Combine filter and DQ rules in same hierarchy. Rejected because:
- Different concerns (filtering vs. validation)
- Filter rules more entity-specific
- Cleaner separation of responsibilities

### 3. Code-based Filters
Define filters in Python code. Rejected because:
- Requires code changes for config updates
- Less accessible to non-developers
- Violates configuration-driven principle

## Provider Defaults

| Provider | Default Batch Size | Notes |
|----------|-------------------|-------|
| ChEMBL | 20 | API optimal |
| PubChem | 1 | SMILES search limitation |
| UniProt | 100 | OR-query batching |
| PubMed | 100 | NCBI E-utilities |
| CrossRef | 50 | Polite pool |
| OpenAlex | 50 | Polite pool |
| SemanticScholar | 100 | Paper lookup |

## Compliance

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Hierarchical merge | PASS | `FilterConfigLoader._deep_merge()` |
| Provider defaults | PASS | `providers/{provider}.yaml` |
| Entity overrides | PASS | `entities/{provider}/{entity}.yaml` |
| Backward compatibility | PASS | Inline `input_filter`/`gold_filters` supported |
| Domain conversion | PASS | `FilterConfigFile.to_domain()` |
| Extraction params | PASS | `extraction_params` section in filter YAML |

## References

- ADR-027: DQ Rules Externalization (pattern reference)
- Domain models: `src/bioetl/domain/filtering/`
- Schema: `src/bioetl/infrastructure/schemas/filter_config.py`
- Loader: `src/bioetl/infrastructure/config/filter_config_loader.py`
- Config files: `configs/filters/`
- Tests: `tests/unit/infrastructure/config/test_filter_config_loader.py`

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-20 | Claude Code | Initial version |
| 2026-02-09 | Claude Code | Added §3 Extraction-Level Filtering (extraction_params) |
