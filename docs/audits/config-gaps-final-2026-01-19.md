# Config Gap Analysis Report

**Date**: 2026-01-19
**Baseline**: ADR-014 (Deterministic Writes), ADR-025 (Config Unification), ADR-027 (DQ Externalization)

## Summary

| Metric | Count |
|--------|-------|
| Total configs analyzed | 20 |
| Standard pipeline configs | 19 |
| Composite pipeline configs | 1 |
| With critical issues | 0 |
| With medium issues | 0 |
| With low issues | 17 |
| Clean (no issues) | 3 |

### Issue Counts by Severity

| Severity | Total Issues |
|----------|-------------|
| Critical (MUST fix) | 0 |
| Medium (SHOULD fix) | 0 |
| Low (MAY fix) | 23 |

## Critical Issues (MUST fix)

✅ No critical issues found!

## Low Issues (MAY fix)

### `chembl/assay.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/assay.yaml but not referenced

### `chembl/assay_parameters.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/assay_parameters.yaml but not referenced

### `chembl/cell_line.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/cell_line.yaml but not referenced

### `chembl/compound_record.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/compound_record.yaml but not referenced

### `chembl/molecule.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/molecule.yaml but not referenced

### `chembl/protein_class.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/protein_class.yaml but not referenced

### `chembl/publication.yaml`
- ℹ️ sink.bronze.path not hierarchical (chembl/document)
- ℹ️ sink.silver.path not hierarchical (chembl/document)
- ℹ️ sink.gold.path not hierarchical (chembl/document)
- ℹ️ No dq_config_file and no DQ file at entities/chembl/document.yaml

### `chembl/publication_similarity.yaml`
- ℹ️ No dq_config_file and no DQ file at entities/chembl/document_similarity.yaml

### `chembl/publication_term.yaml`
- ℹ️ No dq_config_file and no DQ file at entities/chembl/document_term.yaml

### `chembl/target.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/target.yaml but not referenced

### `chembl/target_component.yaml`
- ℹ️ DQ file exists at configs/dq/entities/chembl/target_component.yaml but not referenced

### `crossref/publication.yaml`
- ℹ️ sink.bronze.path not hierarchical (crossref/work)
- ℹ️ sink.silver.path not hierarchical (crossref/work)
- ℹ️ sink.gold.path not hierarchical (crossref/work)
- ℹ️ No dq_config_file and no DQ file at entities/crossref/work.yaml

### `openalex/publication.yaml`
- ℹ️ DQ file exists at configs/dq/entities/openalex/publication.yaml but not referenced

### `pubchem/compound.yaml`
- ℹ️ DQ file exists at configs/dq/entities/pubchem/compound.yaml but not referenced

### `pubmed/publications.yaml`
- ℹ️ DQ file exists at configs/dq/entities/pubmed/publication.yaml but not referenced

### `semanticscholar/publication.yaml`
- ℹ️ DQ file exists at configs/dq/entities/semanticscholar/publication.yaml but not referenced

### `uniprot/protein.yaml`
- ℹ️ DQ file exists at configs/dq/entities/uniprot/protein.yaml but not referenced

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

- [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md): Deterministic Writes
- [ADR-025](../02-architecture/decisions/ADR-025-pipeline-config-unification.md): Pipeline Config Unification
- [ADR-027](../02-architecture/decisions/ADR-027-dq-rules-externalization.md): DQ Rules Externalization
