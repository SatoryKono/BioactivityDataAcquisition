# Config Unification Report

**Date**: 2026-01-19
**Author**: Claude Agent
**Baseline**: ADR-014, ADR-025, ADR-027

## Executive Summary

Pipeline configuration унификация завершена. Все 19 стандартных конфигов и 1 композитный конфиг соответствуют требованиям:
- ADR-014 (Deterministic Writes) - все sink.silver и sink.gold имеют sort_by
- ADR-025 (Pipeline Config Unification) - унифицированная структура конфигов
- ADR-027 (DQ Rules Externalization) - threshold'ы вынесены в внешние DQ файлы

## Changes Summary

### Comparison: Initial vs Final

| Metric | Initial | Final | Delta |
|--------|---------|-------|-------|
| Critical issues | 0 | 0 | = |
| Medium issues | 1 | 0 | -1 |
| Low issues | 24 | 23 | -1 |
| Configs analyzed | 20 | 20 | = |

### Fixed Issues

#### Medium (P1) - Fixed
1. **`uniprot/idmapping.yaml`**: Migrated inline `dq_rules` thresholds to external `dq_config_file` (ADR-027 compliance)

#### Low (P2) - Remaining (by design)
- 17 configs have DQ files that exist but are not explicitly referenced via `dq_config_file`
  - Note: This is not blocking - DQ loader uses hierarchical discovery
- 3 configs have non-hierarchical paths (cosmetic)
- 3 configs have missing DQ files for specific entity paths

## Validation Results

| Check | Result |
|-------|--------|
| `validate_unified_configs.py` | PASS (all 19 standard configs OK, 1 composite skipped) |
| `config_gap_analysis.py` critical | 0 |
| `config_gap_analysis.py` medium | 0 |
| YAML syntax check | PASS (20 files, 0 errors) |
| ConfigLoader smoke test | PASS (7 key configs loaded) |
| Unit tests (config/) | PASS (30 tests) |
| Architecture tests | PASS (989 tests, 15 skipped) |

## Files Modified (This Session)

### Scripts Updated
- `src/tools/scripts/validate_unified_configs.py` - Added composite config exclusion (ADR-026)

### Documentation Created
- `docs/audits/config_gaps_final_2026-01-19.md` - Final gap analysis report
- `docs/audits/config_unification_report_2026-01-19.md` - This report

## Previous Changes (PRs #1637, #1638)

### Pipeline Configs (19 standard + 1 composite)
- `configs/pipelines/chembl/*.yaml` (12 files)
- `configs/pipelines/pubchem/*.yaml` (1 file)
- `configs/pipelines/uniprot/*.yaml` (2 files)
- `configs/pipelines/pubmed/*.yaml` (1 file)
- `configs/pipelines/crossref/*.yaml` (1 file)
- `configs/pipelines/openalex/*.yaml` (1 file)
- `configs/pipelines/semanticscholar/*.yaml` (1 file)
- `configs/pipelines/composite/*.yaml` (1 file) - ADR-026 structure

### DQ Configs (20 files)
- `configs/dq/entities/chembl/*.yaml` (12 files)
- `configs/dq/entities/pubchem/*.yaml` (1 file)
- `configs/dq/entities/uniprot/*.yaml` (2 files)
- `configs/dq/entities/pubmed/*.yaml` (1 file)
- `configs/dq/entities/crossref/*.yaml` (1 file)
- `configs/dq/entities/openalex/*.yaml` (1 file)
- `configs/dq/entities/semanticscholar/*.yaml` (1 file)
- `configs/dq/providers/*.yaml` (provider-level defaults)
- `configs/dq/_defaults.yaml` (global defaults)

### Scripts Created (PR #1637)
- `scripts/config_gap_analysis.py` - Config compliance checker

## Config Structure (ADR-025 Compliance)

All standard pipeline configs now have:

```yaml
# Required fields
pipeline_name: string     # e.g., "chembl_activity"
provider: string          # e.g., "chembl"
entity_type: string       # e.g., "activity"
version: string           # Semantic version
description: string       # Human-readable description
primary_keys: [string]    # List of primary key columns
silver_table: string      # Silver table name
gold_table: string        # Gold table name

# Source configuration
source_file: path         # OR source: {...}

# Sink configuration with ADR-014 compliance
sink:
  bronze:
    path: string
  silver:
    path: string
    primary_key: [string]
    partition_by: [string]
    sort_by:                # ADR-014: deterministic writes
      columns: [string]
      ascending: boolean
    csv_export:
      path: string
  gold:
    path: string
    sort_by:                # ADR-014: deterministic writes
      columns: [string]
      ascending: boolean
    csv_export:
      path: string

# Input filtering
input_filter:
  enabled: boolean

# Gold filters
gold_filters:
  required_fields: [string]

# DQ configuration (ADR-027)
dq_config_file: path      # External DQ config reference
dq_rules: {...}           # Optional inline overrides (field validations only)
```

## Recommendations

### Immediate (done)
- [x] Add `sort_by` to all Silver/Gold sinks (ADR-014 compliance)
- [x] Add missing required fields (version, description, gold_table)
- [x] Migrate inline `dq_rules` thresholds to `dq_config_file` (ADR-027)

### Future Improvements
1. **Add `scripts/config_gap_analysis.py` to CI pipeline**
   - Run on every PR touching `configs/`
   - Fail on critical/medium issues

2. **Explicitly reference DQ configs**
   - Add `dq_config_file` to configs that don't have it
   - Currently using implicit hierarchical discovery

3. **Unify path patterns**
   - Some use `{provider}/{entity_internal_name}` (e.g., `chembl/document`)
   - Others use `{provider}/{entity}` (e.g., `chembl/activity`)
   - Consider standardizing to config-based entity_type

4. **Pre-commit hook for config validation**
   ```yaml
   # .pre-commit-config.yaml
   - repo: local
     hooks:
       - id: validate-configs
         name: Validate pipeline configs
         entry: python src/tools/scripts/validate_unified_configs.py
         language: python
         files: ^configs/pipelines/.*\.yaml$
   ```

## ADR References

- [ADR-014](../../02-architecture/decisions/ADR-014-deterministic-writes.md): Deterministic Writes
- [ADR-025](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md): Pipeline Config Unification
- [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md): Composite Pipeline Pattern
- [ADR-027](../../02-architecture/decisions/ADR-027-dq-rules-externalization.md): DQ Rules Externalization

## Sign-off

- [x] Gap analysis: 0 critical, 0 medium issues
- [x] Validator: All standard configs pass
- [x] YAML syntax: All files valid
- [x] ConfigLoader: Key configs load successfully
- [x] Unit tests: 30/30 pass
- [x] Architecture tests: 989/989 pass (15 skipped)

---

*Generated by Claude Agent on 2026-01-19*
