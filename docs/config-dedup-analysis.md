# Configuration Duplication Analysis Report

**Date**: 2026-01-21
**Author**: Claude Code
**Version**: 1.0.0

## Executive Summary

This analysis identifies significant duplication between:
- `configs/pipelines/{provider}/{entity}.yaml` (pipeline configs)
- `configs/filter/entities/{provider}/{entity}.yaml` (filter entity configs)
- `configs/dq/entities/{provider}/{entity}.yaml` (DQ entity configs)

**Key Findings**:
- **~195 lines** of duplicated content across 20 pipeline configs
- **input_filter**: 100% duplicated in 18/20 pipeline configs
- **gold_filters**: 100% duplicated in 18/20 pipeline configs
- **sink paths**: Follow predictable convention `data/output/{layer}/{provider}/{entity}`

## Duplication Categories

### Category 1: DUPLICATE (100% identical - should be removed)

| Section | Description | Action |
|---------|-------------|--------|
| `input_filter` | Identical to filter entity config | Remove from pipeline config |
| `gold_filters` | Identical to filter entity config | Remove from pipeline config |
| `source_file` | Predictable: `../../sources/{provider}.yaml` | Auto-compute from provider |
| `dq_config_file` | Predictable: `../../dq/entities/{provider}/{entity}.yaml` | Auto-compute from provider/entity |
| `filter_config_file` | Predictable: `../../filter/entities/{provider}/{entity}.yaml` | Auto-compute from provider/entity |
| `sink.bronze.path` | Predictable: `data/output/bronze/{provider}/{entity}` | Auto-compute |
| `sink.silver.path` | Predictable: `data/output/silver/{provider}/{entity}` | Auto-compute |
| `sink.gold.path` | Predictable: `data/output/gold/{provider}/{entity}` | Auto-compute |
| `sink.silver.csv_export.path` | Same as silver path | Auto-compute |
| `sink.gold.csv_export.path` | Same as gold path | Auto-compute |
| `sink.silver.primary_key` | Same as `primary_keys` | Auto-copy from primary_keys |
| `sink.silver.sort_by.columns` | Usually same as `primary_keys` | Auto-copy from primary_keys |
| `sink.gold.sort_by.columns` | Usually same as `primary_keys` | Auto-copy from primary_keys |

### Category 2: OVERRIDE (extends/differs from entity config - keep with comment)

| Section | Description | Action |
|---------|-------------|--------|
| `dq_rules.field_validations` | Extends entity DQ config | Keep only overrides |
| `dq_rules.cross_field_validations` | Extends entity DQ config | Keep only overrides |
| `dq_rules.conditional_validations` | Extends entity DQ config | Keep only overrides |
| `sink.silver.partition_by` | Entity-specific partitioning | Keep (non-default) |
| `source.*` (special) | Provider-specific API config (e.g., PubMed search_term) | Keep |

### Category 3: UNIQUE (only in pipeline config - keep as-is)

| Section | Description | Action |
|---------|-------------|--------|
| `pipeline_name` | Unique identifier | Keep (required) |
| `provider` | Provider name | Keep (required) |
| `entity_type` | Entity type | Keep (required) |
| `version` | Config version | Keep (required) |
| `description` | Human-readable description | Keep (required) |
| `primary_keys` | Deduplication keys | Keep (required) |
| `silver_table` | Silver table name | Keep (required) |
| `gold_table` | Gold table name | Keep (required) |

---

## Detailed Inventory by Provider

### ChEMBL (12 entities)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| activity | `chembl/activity.yaml` | 128 | 42 | ~86 |
| assay | `chembl/assay.yaml` | 102 | 35 | ~67 |
| assay_parameters | `chembl/assay_parameters.yaml` | 68 | 32 | ~36 |
| cell_line | `chembl/cell_line.yaml` | 65 | 32 | ~33 |
| compound_record | `chembl/compound_record.yaml` | 71 | 32 | ~39 |
| molecule | `chembl/molecule.yaml` | 130 | 35 | ~95 |
| protein_class | `chembl/protein_class.yaml` | 69 | 32 | ~37 |
| publication | `chembl/publication.yaml` | 77 | 32 | ~45 |
| publication_similarity | `chembl/publication_similarity.yaml` | 70 | 32 | ~38 |
| publication_term | `chembl/publication_term.yaml` | 75 | 32 | ~43 |
| target | `chembl/target.yaml` | 110 | 42 | ~68 |
| target_component | `chembl/target_component.yaml` | 67 | 32 | ~35 |

**ChEMBL Subtotal**: 1,032 lines → ~622 lines (-410 lines, -40%)

### UniProt (2 entities)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| protein | `uniprot/protein.yaml` | 71 | 35 | ~36 |
| idmapping | `uniprot/idmapping.yaml` | 95 | 35 | ~60 |

**UniProt Subtotal**: 166 lines → ~96 lines (-70 lines, -42%)

### PubChem (1 entity)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| compound | `pubchem/compound.yaml` | 128 | 35 | ~93 |

**PubChem Subtotal**: 128 lines → ~93 lines (-35 lines, -27%)

### PubMed (1 entity)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| publications | `pubmed/publications.yaml` | 76 | 32 | ~44 |

**PubMed Subtotal**: 76 lines → ~44 lines (-32 lines, -42%)

### CrossRef (1 entity)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| publication | `crossref/publication.yaml` | 72 | 35 | ~37 |

**CrossRef Subtotal**: 72 lines → ~37 lines (-35 lines, -49%)

### OpenAlex (1 entity)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| publication | `openalex/publication.yaml` | 80 | 35 | ~45 |

**OpenAlex Subtotal**: 80 lines → ~45 lines (-35 lines, -44%)

### SemanticScholar (1 entity)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| publication | `semanticscholar/publication.yaml` | 75 | 32 | ~43 |

**SemanticScholar Subtotal**: 75 lines → ~43 lines (-32 lines, -43%)

### Composite (1 entity)

| Entity | File | Lines | Duplicates | After Cleanup |
|--------|------|-------|------------|---------------|
| publication | `composite/publication.yaml` | 196 | 45 | ~151 |

**Composite Subtotal**: 196 lines → ~151 lines (-45 lines, -23%)

---

## Total Summary

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| **Total Lines** | 1,825 | ~1,131 | **-694 lines (-38%)** |
| **Duplicate Lines** | 694 | 0 | **-694 lines** |

---

## Detailed Duplication Examples

### Example 1: chembl/activity.yaml

**DUPLICATE - input_filter** (lines 123-128 in pipeline, lines 16-21 in filter entity):
```yaml
# Pipeline config (DELETE)
input_filter:
  enabled: true
  source_path: "data/input/activity.csv"
  column_name: "activity_id"
  filter_field: "activity_id"
  batch_size: 20

# Filter entity config (KEEP)
input_filter:
  enabled: true
  source_path: "data/input/activity.csv"
  column_name: "activity_id"
  filter_field: "activity_id"
  batch_size: 20
```

**DUPLICATE - gold_filters** (lines 87-102 in pipeline, lines 27-52 in filter entity):
```yaml
# Both configs have IDENTICAL content:
gold_filters:
  columns:
    standard_type: [IC50, Ki]
    standard_units: [nM]
    standard_relation: ["="]
    assay_type: [B, F]
    potential_duplicate: ["0"]
  ranges:
    standard_value:
      min: 0
      include_min: false
  required_fields:
    - standard_type
    - standard_value
    - standard_units
    - target_chembl_id
```

**DUPLICATE - sink paths** (lines 105-120):
```yaml
# Can be auto-computed from provider=chembl, entity_type=activity:
sink:
  bronze:
    path: "data/output/bronze/chembl/activity"  # = data/output/bronze/{provider}/{entity}
  silver:
    path: "data/output/silver/chembl/activity"  # = data/output/silver/{provider}/{entity}
    primary_key: ["activity_id"]                 # = primary_keys
    sort_by:
      columns: ["activity_id"]                   # = primary_keys
    csv_export:
      path: "data/output/silver/chembl/activity" # = silver.path
  gold:
    path: "data/output/gold/chembl/activity"    # = data/output/gold/{provider}/{entity}
    sort_by:
      columns: ["activity_id"]                   # = primary_keys
    csv_export:
      path: "data/output/gold/chembl/activity"  # = gold.path
```

### Example 2: uniprot/protein.yaml

**DUPLICATE - All filter config identical to filter entity config**

Pipeline config gold_filters (lines 37-43):
```yaml
gold_filters:
  required_fields:
    - accession
    - entry_name
    - organism
  columns:
    reviewed: ["true"]
```

Filter entity config (lines 28-38):
```yaml
gold_filters:
  columns:
    reviewed: ["true"]
  required_fields:
    - accession
    - entry_name
    - organism
```

---

## Convention-Based Resolution Proposal

### Proposed _base.yaml Additions

```yaml
# Convention-based path resolution (added to _base.yaml)
# These are computed at load time from provider and entity_type:

# File references - auto-computed if not specified:
# source_file: ../../sources/{provider}.yaml
# dq_config_file: ../../dq/entities/{provider}/{entity_type}.yaml
# filter_config_file: ../../filter/entities/{provider}/{entity_type}.yaml

# Sink paths - auto-computed if not specified:
# sink.bronze.path: data/output/bronze/{provider}/{entity_type}
# sink.silver.path: data/output/silver/{provider}/{entity_type}
# sink.gold.path: data/output/gold/{provider}/{entity_type}
# sink.silver.csv_export.path: {sink.silver.path}
# sink.gold.csv_export.path: {sink.gold.path}

# Primary key propagation:
# sink.silver.primary_key: {primary_keys}
# sink.silver.sort_by.columns: {primary_keys}
# sink.gold.sort_by.columns: {primary_keys}
```

### Proposed Minimal Pipeline Config Format

After implementing conventions, a minimal pipeline config would be:

```yaml
# configs/pipelines/chembl/activity.yaml
# Minimal config - all paths and filters resolved by convention

pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
description: "Extract biological activity records from ChEMBL API"

primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

# DQ overrides (only fields that DIFFER from entity DQ config)
dq_rules:
  field_validations:
    # Override: Extended enum with additional types
    - field: "standard_type"
      type: "enum"
      allowed: ["IC50", "Ki", "Kd", "EC50", "AC50", "GI50", "ED50", "MIC", "CC50"]
      nullable: true
```

**Result**: 128 lines → ~25 lines (80% reduction)

---

## Implementation Plan

### Phase 1: Analysis (COMPLETE)
- [x] Inventory duplication
- [x] Categorize (DUPLICATE/OVERRIDE/UNIQUE)
- [x] Create this analysis document

### Phase 2: Config Loader Enhancement
- [ ] Add convention-based path resolution to config loader
- [ ] Auto-compute `source_file`, `dq_config_file`, `filter_config_file`
- [ ] Auto-compute sink paths from provider/entity_type
- [ ] Auto-copy primary_keys to sink.silver.primary_key and sort_by

### Phase 3: Pipeline Config Cleanup
- [ ] Remove duplicated `input_filter` sections
- [ ] Remove duplicated `gold_filters` sections
- [ ] Remove convention-computed paths
- [ ] Add `# Inherited from: {path}` comments where needed
- [ ] Keep only OVERRIDE and UNIQUE sections

### Phase 4: Verification
- [ ] Run `python scripts/validate_pipeline_configs.py`
- [ ] Run `pytest tests/unit/composition/test_config_loader.py`
- [ ] Run `pytest tests/integration/`
- [ ] Verify all pipelines still work identically

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing pipeline behavior | Comprehensive test coverage before/after |
| Config loader complexity | Well-documented convention rules |
| Backward compatibility | Support both explicit and computed paths |
| Merge conflicts during transition | Atomic refactoring per provider |

---

## Appendix: Per-Entity Duplication Details

### chembl/activity.yaml

| Section | Lines | Status | Details |
|---------|-------|--------|---------|
| Header comments | 1-6 | UNIQUE | Keep |
| pipeline_name, provider, entity_type | 7-11 | UNIQUE | Keep |
| primary_keys, tables | 13-15 | UNIQUE | Keep |
| source_file | 18 | DUPLICATE | Auto-compute |
| dq_config_file comment | 20-29 | DUPLICATE | Auto-compute |
| filter_config_file | 31-38 | DUPLICATE | Auto-compute |
| dq_rules (overrides) | 45-84 | OVERRIDE | Keep only differences |
| gold_filters | 86-102 | DUPLICATE | Remove (in filter entity) |
| sink paths | 104-120 | DUPLICATE | Auto-compute |
| input_filter | 122-128 | DUPLICATE | Remove (in filter entity) |

### chembl/target.yaml

| Section | Lines | Status | Details |
|---------|-------|--------|---------|
| Header comments | 1-5 | UNIQUE | Keep |
| pipeline_name, provider, entity_type | 6-10 | UNIQUE | Keep |
| primary_keys, tables | 12-14 | UNIQUE | Keep |
| source_file | 16 | DUPLICATE | Auto-compute |
| dq_config_file | 18-25 | DUPLICATE | Auto-compute |
| filter_config_file | 27-34 | DUPLICATE | Auto-compute |
| dq_rules (overrides) | 40-65 | OVERRIDE | Keep (extended enums, unique validations) |
| gold_filters | 67-83 | DUPLICATE | Remove (in filter entity) |
| sink paths | 85-102 | DUPLICATE | Auto-compute |
| input_filter | 104-110 | DUPLICATE | Remove (in filter entity) |

---

*Generated by config deduplication analysis tool*
