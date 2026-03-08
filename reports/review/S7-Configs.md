# Code Review Report — S7: Configs
**Date**: 2026-03-08
**Scope**: configs/
**Files reviewed**: 47
**Status**: FAIL
**Score**: 5.0/10.0
---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Configs | 5 | 0 | 5 | 0 | 0 | 5.0 |

## High Issues
### ADR-039: Deprecated `primary_keys`
- **Severity**: HIGH
- **Files**: `configs/entities/semanticscholar/publication.yaml:1`, `configs/entities/crossref/publication.yaml:1`, `configs/entities/openalex/publication.yaml:1`, `configs/entities/pubmed/publication.yaml:1`, `configs/entities/uniprot/idmapping.yaml:1`
- **Description**: Config pattern: Pipeline configuration files (YAML) must use `business_primary_keys` and `technical_primary_key`. The `primary_keys` field is deprecated and triggers CI invariant test failures.

## Positive Observations
- **ADR-014**: All Silver/Gold sinks utilize `sort_by` correctly.
- **ADR-027**: No inline Data Quality thresholds detected.
