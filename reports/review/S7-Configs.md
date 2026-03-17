# Consolidated Review — S7: Configs
**Date**: 2026-03-17
**Sub-reviews**: 3 agents
**Status**: FAIL
**Consolidated Score**: 7.9
## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S7.1 — Subzone_1 | 20 | 10.0 | PASS | 0 | 0 |
| S7.2 — Subzone_2 | 20 | 5.0 | FAIL | 0 | 5 |
| S7.3 — Subzone_3 | 8 | 10.0 | PASS | 0 | 0 |
## Aggregated Issues
### Critical (MUST fix)
### High
- **ADR-014**: `configs/entities/semanticscholar/publication.yaml:0` - Missing sort_by in sink config
- **ADR-014**: `configs/entities/crossref/publication.yaml:0` - Missing sort_by in sink config
- **ADR-014**: `configs/entities/openalex/publication.yaml:0` - Missing sort_by in sink config
- **ADR-014**: `configs/entities/pubmed/publication.yaml:0` - Missing sort_by in sink config
- **ADR-014**: `configs/entities/chembl/publication.yaml:0` - Missing sort_by in sink config
## Cross-subzone Observations
Dynamically aggregated reports successfully verified dependencies.
## Top 5 Recommendations
1. Fix any cross-layer boundary violations.
2. Adopt strict typing across all zones.