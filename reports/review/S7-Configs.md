# Consolidated Review — S7: Configs
**Date**: 2026-03-22
**Sub-reviews**: 3 agents
**Status**: WARN
**Consolidated Score**: 9.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S7.1 — Part 1 | 20 | 7.6 | WARN | 0 | 8 |
| S7.2 — Part 2 | 20 | 9.7 | PASS | 0 | 1 |
| S7.3 — Part 3 | 13 | 10.0 | PASS | 0 | 0 |

## Aggregated Issues
### Critical (MUST fix)

### High
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/crossref.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/chembl.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/pubmed.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/openalex.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/pubchem.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/uniprot.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/providers/semanticscholar.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/base/quality.yaml:1`
- **ADR-027**: Inline DQ thresholds found instead of external reference. in `configs/entities/uniprot/idmapping.yaml:1`

## Cross-subzone Observations
- Need stricter import boundary enforcement.
- Consistent typing is present but some Any usage remains.

## Top 5 Recommendations
1. Fix critical import boundary violations.
2. Replace direct structlog imports with LoggerPort.
3. Add missing type annotations to public methods.
