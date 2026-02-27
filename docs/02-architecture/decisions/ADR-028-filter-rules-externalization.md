# ADR-028: Filter Rules Externalization

**Status:** Accepted
**Date:** 2026-02-09
**Decision makers:** @BioETL-Team

## Context

Filter configurations (`input-filter` and `gold-filters`) were embedded directly in pipeline YAML configuration files (`configs/entities/{provider}/{entity}.yaml`). This caused several problems:

1. **Duplication**: Same filter patterns repeated across pipelines (e.g., batch-size defaults)
2. **Maintenance burden**: Changing global filter policies required editing multiple files
3. **No reusability**: Impossible to share filter patterns across providers/entities
4. **SRP violation**: Pipeline config mixed orchestration and filtering concerns

Example of duplication:
```yaml
# configs/entities/chembl/activity.yaml
input-filter:
  batch-size: 20

# configs/entities/chembl/molecule.yaml
input-filter:
  batch-size: 20  # Duplicated provider default
```

This pattern follows ADR-027 (DQ Rules Externalization) to create a consistent hierarchical configuration system.

## Decision

Extract filter rules into a hierarchical configuration structure:

```
configs/filters/
├── -defaults.yaml           # Global defaults (Level 1)
├── README.md                # Documentation
├── providers/
│   └── {provider}.yaml      # Provider overrides (Level 2)
└── entities/
    └── {provider}/
        └── {entity}.yaml    # Entity-specific rules (Level 3)
```

**Merge priority** (later wins for scalars, special handling for collections):
1. `-defaults.yaml`
2. `providers/{provider}.yaml`
3. `entities/{provider}/{entity}.yaml`
4. Inline `filter-rules` in pipeline config (for exceptional cases)

Pipeline configs reference filter config via `filter-config-file`:
```yaml
pipeline-name: chembl_activity
filter-config-file: ../../filters/entities/chembl/activity.yaml
```

### Implementation Components

1. **Pydantic schemas**: `src/bioetl/infrastructure/schemas/filter-config.py`
   - `InputFilterFileConfig`: Input filter configuration
   - `GoldFiltersFileConfig`: Gold layer filter configuration
   - `FilterConfigFile`: Complete schema with to-domain() conversion

2. **Configuration loader**: `src/bioetl/infrastructure/config/filter-config-loader.py`
   - `FilterConfigLoader.load(provider, entity, inline-overrides)`: Merges and returns domain objects
   - `FilterConfigLoader.load-as-dict(provider, entity, inline-overrides)`: Merges and returns raw dict (used by pipeline config loading)
   - `FilterConfigLoader.-merge-hierarchy()`: Shared 4-level merge logic
   - Thread-safe caching for performance
   - Deep merge with list deduplication for required-fields/exclude-if-present

3. **Pipeline config integration**: `src/bioetl/infrastructure/config-loader.py`
   - `-apply-hierarchical-filter-config()`: Single entry point for filter merge during pipeline loading
   - Delegates to `FilterConfigLoader.load-as-dict()` for the full hierarchy
   - Collects inline overrides from pipeline YAML (`input-filter`, `gold-filters`, `silver-filters`, `extraction-params`, `filter-rules`)

4. **Config files**: `configs/filters/`
   - `-defaults.yaml`: Global defaults (batch-size=100)
   - `providers/{provider}.yaml`: Provider-specific settings (e.g., ChEMBL batch-size=1000)
   - `entities/{provider}/{entity}.yaml`: Entity-specific rules

5. **Pipeline schema**: `src/bioetl/infrastructure/schemas/pipeline-config.py`
   - `filter-config-file` field for convention-based path (informational)
   - `filter-rules` field for inline overrides
   - Legacy `input-filter`/`gold-filters` fields retained for backward compatibility

## Consequences

### Positive

- **DRY**: Provider-level defaults (e.g., ChEMBL batch-size=20) defined once
- **Separation of Concerns**: Pipeline config focuses on orchestration
- **Reusability**: Provider-level filters shared across entities
- **Flexibility**: Entity-specific rules without affecting others
- **Backward compatible**: Inline `input-filter`/`gold-filters` still supported
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
| Scalars | Override (later wins) | `batch-size: 50` replaces `100` |
| `required-fields` | Concatenate with dedup | Entity fields added to provider |
| `exclude-if-present` | Concatenate with dedup | Entity exclusions added to provider |
| Nested dicts (`columns`, `ranges`, etc.) | Recursive merge | Entity columns merged with provider |
| Other lists | Override (later wins) | `columns.field: [A, B]` replaces `[X, Y]` |

## Filter Types

### Input Filter Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `enabled` | bool | Enable/disable input filtering |
| `source-path` | str | Path to CSV file with filter IDs |
| `column-name` | str | CSV column with primary IDs |
| `filter-field` | str | API field to filter by |
| `batch-size` | int | IDs per API request (1-1000) |
| `fallback-column` | str | Optional fallback search field |

### Gold Filter Types

| Filter | Parameters | Description |
|--------|------------|-------------|
| `required-fields` | list[str] | Fields must be non-null |
| `columns` | dict[str, list] | Value inclusion list |
| `ranges` | dict[str, Range] | Numeric bounds |
| `list-lengths` | dict[str, MinMax] | List size constraints |
| `list-contains` | dict[str, Contains] | List content filter |
| `exclude-if-present` | list[str] | Exclude if field has value |

### §3. Extraction-Level Filtering (extraction-params)

#### Назначение

Серверные query parameters для API-провайдеров, применяемые на этапе
Bronze extraction. Сокращают объём трафика — API возвращает только
релевантные записи вместо полного датасета.

#### Область применения

- Только Bronze extract, не влияет на transform/load
- Provider-specific синтаксис (ChEMBL: `--in`, `--isnull`, `--gt` и др.)
- Параметры НЕ влияют на content-hash (ADR-014)

#### Конфигурация

Размещается в `configs/filters/` hierarchy как секция `extraction-params`:

```yaml
# configs/filters/entities/chembl/activity.yaml
extraction-params:
  standard-type--in: "IC50,Ki"
  standard-units: "nM"
  standard-relation: "="
  assay-type--in: "B,F"
  potential-duplicate: 0
  data-validity-comment--isnull: true
  pchembl-value--isnull: false
  standard-flag: 1
```

#### Merge order

`configs/filters/-defaults.yaml` → `providers/{provider}.yaml`
→ `entities/{provider}/{entity}.yaml`

Entity-level `extraction-params` полностью заменяет provider-level
(не merge отдельных ключей, а full override секции).

#### Взаимодействие с input-filter

- `extraction-params`: фильтрует по СВОЙСТВАМ записей (статические, из YAML)
- `input-filter`: фильтрует по ID (динамические, из CSV)
- Применяются совместно (AND семантика в API запросе)
- При пересечении ключей — WARNING, `input-filter` override

#### Взаимодействие с gold-filters

- `extraction-params`: pre-extract (API-side)
- `gold-filters`: post-load (client-side, Silver→Gold)
- Не конфликтуют — разные точки применения

#### Ограничения

- НЕТ CLI override (детерминизм, ADR-014)
- MUST логироваться в `SourceMetadata.query-string`
- Provider-specific: не все провайдеры поддерживают серверную фильтрацию

#### Domain representation

`ExtractionParams` frozen dataclass в `domain/models/filter.py`

### Filter Type Comparison

| Aspect | `input-filter` (§1) | `gold-filters` (§2) | `extraction-params` (§3) |
|--------|---------------------|----------------------|--------------------------|
| Stage | Bronze extract | Silver→Gold transform | Bronze extract |
| Side | Client-side (ID batching) | Client-side (DataFrame) | Server-side (API query) |
| Source | CSV file (dynamic) | YAML (static) | YAML (static) |
| Filters by | Record IDs | Field values, ranges, nulls | Record properties |
| Merge behavior | Recursive merge | Recursive merge | Full override (section-level) |
| CLI override | No (ADR-014) | No (ADR-014) | No (ADR-014) |
| Affects content-hash | No (ADR-014) | No | No (ADR-014) |
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
| ChEMBL | 1000 | API optimal (entity-level overrides: molecule=20, activity=1500) |
| PubChem | 1 | SMILES search limitation |
| UniProt | 100 | OR-query batching |
| PubMed | 100 | NCBI E-utilities |
| CrossRef | 50 | Polite pool |
| OpenAlex | 50 | Polite pool |
| SemanticScholar | 100 | Paper lookup |

## Compliance

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Hierarchical merge | PASS | `FilterConfigLoader.-merge-hierarchy()` |
| Single merge mechanism | PASS | Consolidated into `FilterConfigLoader` (no duplication) |
| Provider defaults | PASS | `providers/{provider}.yaml` |
| Entity overrides | PASS | `entities/{provider}/{entity}.yaml` |
| Inline overrides | PASS | `filter-rules` / inline sections in pipeline YAML |
| Backward compatibility | PASS | Inline `input-filter`/`gold-filters` supported |
| Domain conversion | PASS | `FilterConfigFile.to-domain()` |
| Extraction params | PASS | `extraction-params` section in filter YAML |
| Silver filters | PASS | `silver-filters` section now loaded from hierarchy |

## References

- ADR-027: DQ Rules Externalization (pattern reference)
- Domain models: `src/bioetl/domain/filtering/`
- Schema: `src/bioetl/infrastructure/schemas/filter-config.py`
- Loader: `src/bioetl/infrastructure/config/filter-config-loader.py`
- Pipeline integration: `src/bioetl/infrastructure/config-loader.py` (`-apply-hierarchical-filter-config`)
- Config files: `configs/filters/`
- Tests: `tests/unit/infrastructure/config/test-filter-config-loader.py`

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-20 | Claude Code | Initial version |
| 2026-02-09 | Claude Code | Added §3 Extraction-Level Filtering (extraction-params) |
| 2026-02-17 | Claude Code | Consolidated filter merge: removed legacy `-load-filter-config`/`-merge-filter-config` from `config-loader.py`, unified via `FilterConfigLoader.-merge-hierarchy()`. All 4 filter sections (`input-filter`, `silver-filters`, `gold-filters`, `extraction-params`) now load from full hierarchy. |
| 2026-02-17 | Claude Code | Fixed: ChEMBL provider batch-size in table: 20 → 1000 (actual provider default) |
