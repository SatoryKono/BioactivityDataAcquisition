# Config Gap Analysis Report

**Date**: 2026-01-23
**Baseline**: ADR-014 (Deterministic Writes), ADR-025 (Config Unification), ADR-027 (DQ Externalization)

## Summary

| Metric | Count |
|--------|-------|
| Total configs analyzed | 20 |
| Standard pipeline configs | 19 |
| Composite pipeline configs | 1 |
| With critical issues | 4 |
| With medium issues | 3 |
| With low issues | 19 |
| Clean (no issues) | 1 |

### Issue Counts by Severity

| Severity | Total Issues |
|----------|-------------|
| Critical (MUST fix) | 8 |
| Medium (SHOULD fix) | 6 |
| Low (MAY fix) | 29 |

## Critical Issues (MUST fix)

### `chembl/activity.yaml`
- ❌ Missing sink.silver section

### `chembl/assay.yaml`
- ❌ Missing sink.silver.sort_by (ADR-014)
- ❌ Missing sink.silver.primary_key (ADR-025)

### `pubmed/publications.yaml`
- ❌ Missing sink.silver.sort_by (ADR-014)
- ❌ Missing sink.silver.primary_key (ADR-025)
- ❌ Missing sink.gold.sort_by (ADR-014)

### `uniprot/protein.yaml`
- ❌ Missing sink.silver.sort_by (ADR-014)
- ❌ Missing sink.silver.primary_key (ADR-025)

## Medium Issues (SHOULD fix)

### `chembl/activity.yaml`
- ⚠️ Missing sink.gold section
- ⚠️ Missing sink.bronze section

### `chembl/assay.yaml`
- ⚠️ Missing sink.gold section
- ⚠️ Missing sink.bronze section

### `uniprot/protein.yaml`
- ⚠️ Missing sink.gold section
- ⚠️ Missing sink.bronze section

## Low Issues (MAY fix)

### `chembl/activity.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/activity.yaml but not referenced
- ℹ️ Missing gold_filters section

### `chembl/assay.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/assay.yaml but not referenced
- ℹ️ Missing gold_filters section

### `chembl/assay_parameters.yaml`
- ℹ️ Missing gold_filters section

### `chembl/cell_line.yaml`
- ℹ️ Missing gold_filters section

### `chembl/compound_record.yaml`
- ℹ️ Missing gold_filters section

### `chembl/molecule.yaml`
- ℹ️ Missing gold_filters section

### `chembl/protein_class.yaml`
- ℹ️ Missing gold_filters section

### `chembl/publication.yaml`
- ℹ️ sink.bronze.path not hierarchical (chembl/document)
- ℹ️ sink.silver.path not hierarchical (chembl/document)
- ℹ️ sink.gold.path not hierarchical (chembl/document)
- ℹ️ Missing gold_filters section

### `chembl/publication_similarity.yaml`
- ℹ️ Missing gold_filters section

### `chembl/publication_term.yaml`
- ℹ️ Missing gold_filters section

### `chembl/target.yaml`
- ℹ️ Missing gold_filters section

### `chembl/target_component.yaml`
- ℹ️ Missing gold_filters section

### `crossref/publication.yaml`
- ℹ️ sink.bronze.path not hierarchical (crossref/work)
- ℹ️ sink.silver.path not hierarchical (crossref/work)
- ℹ️ sink.gold.path not hierarchical (crossref/work)
- ℹ️ Missing gold_filters section

### `openalex/publication.yaml`
- ℹ️ Missing gold_filters section

### `pubchem/compound.yaml`
- ℹ️ Missing gold_filters section

### `pubmed/publications.yaml`
- ℹ️ DQ file exists at configs/dq/entities/pubmed/publication.yaml but not referenced
- ℹ️ Missing gold_filters section

### `semanticscholar/publication.yaml`
- ℹ️ Missing gold_filters section

### `uniprot/idmapping.yaml`
- ℹ️ Missing gold_filters section

### `uniprot/protein.yaml`
- ℹ️ DQ file exists at configs/dq/entities/uniprot/protein.yaml but not referenced
- ℹ️ Missing gold_filters section

## Recommended Actions

### Priority 0 (Critical - Blocks CI)
1. Add `sort_by` to all silver sinks (ADR-014 compliance)
2. Add `sort_by` to all gold sinks where gold.enabled=true (ADR-014)
3. Add `primary_key` to all silver sinks (ADR-025 compliance)
4. Add required fields: `pipeline_name`, `provider`, `entity_type`, `primary_keys`, `silver_table`

### Priority 1 (Medium - Should Fix)
1. Add `version`, `description`, `gold_table` where missing (ADR-025)
2. Migrate inline `dq_rules` thresholds to `dq_config_file` (ADR-027)
3. Add missing `sink.bronze` and `sink.gold` sections

### Priority 2 (Low - Nice to Have)
1. Unify path patterns to `{provider}/{entity}` hierarchy
2. Reference existing DQ config files via `dq_config_file`
3. Add `gold_filters.required_fields` where missing

## ADR References

- [ADR-014](docs/02-architecture/decisions/ADR-014-deterministic-writes.md): Deterministic Writes
- [ADR-025](docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md): Pipeline Config Unification
- [ADR-027](docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md): DQ Rules Externalization
