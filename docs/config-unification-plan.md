# Config Unification Plan

**Version:** 1.0
**Date:** 2026-01-06
**Status:** In Progress

## Executive Summary

Analysis of 20 pipeline configs (1 defaults + 19 entity configs) revealed:
- **129 unique parameters** across all configs
- **21 parameters** present in ALL entity configs (consistent)
- **~50 parameters** with inconsistent presence (partial coverage)
- **16 parameters** only in `_defaults.yaml` (never overridden)

### Key Structural Issues

| Issue | Severity | Configs Affected |
|-------|----------|------------------|
| Missing `gold_table` | Medium | 11/19 entity configs |
| Missing `sink.silver.partition_by` | Low | 3/19 (activity, cell_line, crossref) |
| Missing `sink.silver.primary_key` | Medium | 2/19 (protein_class, target_component) |
| `source` vs `source_file` inconsistency | High | 3 use inline `source` |
| `transform` block presence | Info | 7/19 have it (non-ChEMBL) |
| `dq_rules`/`circuit_breaker` override | Info | Only 1 config (idmapping) |

---

## Discrepancy Categories

### Category A: Missing in _defaults (Entity-Specific - Expected)

These parameters are intentionally entity-specific and should NOT be in defaults:

| Parameter | Reason |
|-----------|--------|
| `pipeline_name` | Unique per entity |
| `provider` | Varies by provider |
| `entity_type` | Unique per entity |
| `description` | Entity-specific description |
| `primary_keys` | Different PKs per entity |
| `silver_table` | Named per entity |
| `gold_table` | Named per entity |
| `source_file` | Reference to provider source |
| `gold_filters.*` | Entity-specific filtering rules |

### Category B: Entity-Specific Overrides (Expected)

These overrides are legitimate and should remain:

| Override | Configs | Reason |
|----------|---------|--------|
| `dq_rules` | uniprot/idmapping | Higher thresholds for ID mapping |
| `circuit_breaker` | uniprot/idmapping | Custom settings |
| `rate_limit` | uniprot/idmapping | UniProt API limits |
| `batch_size` | protein_class, target_component | Full-load strategy |
| `sink.bronze.enabled: false` | uniprot/idmapping | No Bronze for API-only source |

### Category C: Inconsistent Presence (Needs Unification)

| Parameter | Current State | Target State |
|-----------|---------------|--------------|
| `gold_table` | 8/19 have it | ALL should have it (default = silver_table) |
| `sink.silver.partition_by` | 16/19 have it | ALL should have it ([] if none) |
| `sink.silver.primary_key` | 17/19 have it | ALL should have it |
| `transform` | 7/19 have it | REMOVE (not used by code) |
| `source` (inline) | 3/19 have it | Consolidate with source_file |

### Category D: Value Inconsistency (Needs Review)

| Parameter | Variation | Resolution |
|-----------|-----------|------------|
| `sink.bronze.path` | Mixed formats | Standardize to `data/output/bronze` |
| `sink.silver.path` | Mixed formats | Standardize to `data/output/silver` |
| `sink.gold.path` | Mixed formats | Standardize to `data/output/gold` |
| `input_filter.batch_size` | 1-1000 | Keep varied (API-specific) |

### Category E: Structural Inconsistency

#### E1: `source` vs `source_file`

**Current state:**
- 18 configs use `source_file: ../../sources/{provider}.yaml`
- 3 configs have inline `source` block (openalex, pubmed, uniprot/idmapping)
- 2 configs have BOTH (openalex, pubmed)

**Resolution:**
- Keep `source_file` as reference to provider source config
- Inline `source` should be for pipeline-specific overrides only
- Configs with both should use `source` for overrides only

#### E2: `transform` block

**Current state:**
- Only 7 configs have `transform` (non-ChEMBL providers)
- Transform steps are NOT currently used by application code

**Resolution:**
- REMOVE `transform` from all configs (Phase 2)
- If needed later, add to _defaults with empty steps

### Category F: Unused Parameters in _defaults

These are in _defaults but never overridden (verify if used by code):

| Parameter | Status |
|-----------|--------|
| `defaults_version` | Keep (documentation) |
| `maintenance.*` | Keep (future use) |
| `sink.bronze.deterministic` | Keep (code uses) |
| `sink.bronze.format` | Keep (code uses) |
| `sink.bronze.save_json` | Keep (code uses) |
| `sink.silver.forensic_retention` | Keep (code uses) |
| `sink.silver.on_schema_mismatch` | Keep (code uses) |
| `sink.gold.validation.strict` | Keep (code uses) |

---

## Canonical Structure

### Required Parameters (MUST be in every entity config)

```yaml
# Metadata (REQUIRED)
pipeline_name: str          # Unique pipeline identifier
provider: str               # Provider name (chembl, pubchem, uniprot, etc.)
entity_type: str            # Entity type
version: str                # Config version (semver)
description: str            # Human-readable description

# Schema (REQUIRED)
primary_keys: list[str]     # Primary key fields
silver_table: str           # Silver table name
gold_table: str             # Gold table name (defaults to silver_table if omitted)

# Source (REQUIRED - one of these)
source_file: str            # Reference to source config (preferred)
# OR
source: {}                  # Inline source config (for special cases)

# Filters (REQUIRED)
gold_filters:
  required_fields: list[str]  # REQUIRED: fields that must be non-null
  columns: {}                 # OPTIONAL: column value filters
  ranges: {}                  # OPTIONAL: numeric range filters
  list_lengths: {}            # OPTIONAL: list length constraints
  list_contains: {}           # OPTIONAL: list containment checks

# Sink (REQUIRED - paths)
sink:
  bronze:
    path: str               # Bronze output path
  silver:
    path: str               # Silver output path
    primary_key: list[str]  # Primary key for merge
    partition_by: list[str] # Partition columns ([] if none)
    csv_export:
      path: str             # CSV export path
  gold:
    path: str               # Gold output path
    csv_export:
      path: str             # CSV export path

# Input Filter (REQUIRED)
input_filter:
  enabled: bool             # Whether filtering is enabled
  source_path: str          # Input CSV path (if enabled)
  column_name: str          # Column in CSV (if enabled)
  filter_field: str         # Field to filter by (if enabled)
  batch_size: int           # Batch size (from _defaults if not specified)
```

### Optional Parameters (MAY override _defaults)

```yaml
# Override DQ thresholds (rare)
dq_rules:
  soft_fail_threshold: float  # Default: 0.05
  hard_fail_threshold: float  # Default: 0.20

# Override circuit breaker (rare)
circuit_breaker:
  failure_threshold: int      # Default: 5
  recovery_timeout: int       # Default: 300

# Override rate limits (rare)
rate_limit:
  requests_per_second: float
  burst: int

# Entity-specific batch settings
batch_size: int
checkpoint_interval: int

# Sort configuration (optional)
sink:
  silver:
    sort_by:
      columns: list[str]
      ascending: bool
  gold:
    sort_by:
      columns: list[str]
      ascending: bool
```

### Parameters to Remove

These should be removed from entity configs (redundant with _defaults):

```yaml
# REMOVE - use _defaults
sink.silver.format: delta
sink.silver.mode: merge
sink.silver.classification: public
sink.silver.csv_export.enabled: true
sink.silver.csv_export.delimiter: ","
sink.silver.csv_export.header: true
sink.silver.csv_export.encoding: "utf-8"
sink.gold.enabled: true
sink.gold.format: delta
sink.gold.mode: overwrite
sink.gold.csv_export.enabled: true
sink.gold.csv_export.delimiter: ","
sink.gold.csv_export.header: true
sink.gold.csv_export.encoding: "utf-8"

# REMOVE - not used by code
transform: {}
```

---

## Migration Plan

### Phase 1: Add Missing Required Parameters

For each config, add missing required parameters:

| Config | Add `gold_table` | Add `partition_by` | Add `primary_key` |
|--------|------------------|-------------------|-------------------|
| chembl/activity | ✓ `chembl_activity` | ✓ `[]` | — |
| chembl/assay | ✓ `chembl_assay` | — | — |
| chembl/assay_parameters | ✓ `chembl_assay_parameters` | — | — |
| chembl/cell_line | ✓ `chembl_cell_line` | ✓ `[]` | — |
| chembl/compound_record | ✓ `chembl_compound_record` | — | — |
| chembl/document | ✓ `chembl_document` | — | — |
| chembl/document_similarity | ✓ `chembl_document_similarity` | — | — |
| chembl/document_term | ✓ `chembl_document_term` | — | — |
| chembl/molecule | ✓ `chembl_molecule` | — | — |
| chembl/protein_class | — | — | ✓ `[protein_class_id]` |
| chembl/target | ✓ `chembl_target` | — | — |
| chembl/target_component | — | — | ✓ `[component_id]` |
| crossref/publication_enrichment | ✓ `crossref_publication` | ✓ `[]` | — |
| openalex/publication | — | — | — |
| pubchem/compound | — | — | — |
| pubmed/publications | — | — | — |
| semanticscholar/publication | — | — | — |
| uniprot/idmapping | — | — | — |
| uniprot/protein | — | — | — |

### Phase 2: Remove Redundant Parameters

Remove parameters that duplicate _defaults:
- `sink.silver.format`
- `sink.silver.mode`
- `sink.silver.classification`
- `sink.gold.format`
- `sink.gold.mode`
- `sink.silver.csv_export.enabled/delimiter/header/encoding`
- `sink.gold.csv_export.enabled/delimiter/header/encoding`

**Exception:** Keep in uniprot/idmapping (has legitimate overrides)

### Phase 3: Remove Unused Parameters

Remove `transform` block from all configs (not used by code).

### Phase 4: Standardize Paths

Standardize sink paths to consistent format:
- Bronze: `data/output/bronze`
- Silver: `data/output/silver`
- Gold: `data/output/gold`

**Exception:** Keep custom paths where provider-specific (protein_class, target_component, etc.)

### Phase 5: Consolidate `source` vs `source_file`

For configs with both:
- openalex/publication: Keep `source` only for email/batch_size overrides
- pubmed/publications: Keep `source` only for search_term/email/api_key overrides
- uniprot/idmapping: Keep `source` (no source_file reference)

---

## Validation Checklist

After migration, validate each config:

- [ ] Has `pipeline_name`, `provider`, `entity_type`, `version`, `description`
- [ ] Has `primary_keys`, `silver_table`, `gold_table`
- [ ] Has `source_file` OR `source` (not both unless override)
- [ ] Has `gold_filters.required_fields`
- [ ] Has `sink.bronze.path`
- [ ] Has `sink.silver.path`, `sink.silver.primary_key`, `sink.silver.partition_by`
- [ ] Has `sink.gold.path`
- [ ] Has `input_filter.enabled`
- [ ] No duplicate parameters from `_defaults`
- [ ] No `transform` block (removed)

---

## Implementation Order

1. **Backup** all configs
2. **Update _defaults.yaml** (if needed)
3. **Migrate chembl/* configs** (12 files)
4. **Migrate pubchem/compound** (1 file)
5. **Migrate uniprot/* configs** (2 files)
6. **Migrate crossref/* config** (1 file)
7. **Migrate openalex/* config** (1 file)
8. **Migrate pubmed/* config** (1 file)
9. **Migrate semanticscholar/* config** (1 file)
10. **Run validation script**
11. **Run tests**: `make test`

---

## Appendix: Config Template

```yaml
# configs/pipelines/{provider}/{entity}.yaml
# Pipeline configuration for {Provider} {Entity} entity.
#
# Inherits defaults from ../_defaults.yaml

pipeline_name: {provider}_{entity}
provider: {provider}
entity_type: {entity}
version: "1.0.0"
description: "Extract {entity} records from {Provider}"

primary_keys: ["{entity}_id"]
silver_table: "{provider}_{entity}"
gold_table: "{provider}_{entity}"

source_file: ../../sources/{provider}.yaml

gold_filters:
  required_fields:
    - {entity}_id
  columns: {}
  ranges: {}

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["{entity}_id"]
    partition_by: []
    csv_export:
      path: "data/output/csv/silver"
  gold:
    path: "data/output/gold"
    csv_export:
      path: "data/output/csv/gold"

input_filter:
  enabled: true
  source_path: "data/input/{entity}.csv"
  column_name: "{entity}_id"
  filter_field: "{entity}_id"
  batch_size: 100
```
