# Consolidated Review — S6: Tests
**Date**: 2026-03-31
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 9.67

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 167 | 10.00 | PASS | 0 | 0 |
| S6.2 — Unit Domain | 170 | 10.00 | PASS | 0 | 0 |
| S6.3 — Unit Application | 234 | 10.00 | PASS | 0 | 0 |
| S6.4 — Unit Infrastructure | 253 | 10.00 | PASS | 0 | 0 |
| S6.5 — Unit Composition+Misc | 178 | 9.75 | PASS | 0 | 1 |
| S6.6 — Integration+E2E+Security | 133 | 7.50 | WARN | 0 | 14 |

## Aggregated Issues
### Critical (MUST fix)
*None*

### High
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/unit/composition/test_bootstrap_logger.py:9`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/test_uniprot_pipeline.py:90`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/test_pubchem_pipeline.py:92`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/base.py:11`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_pubmed_date_normalization.py:55`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_crossref_date_normalization.py:56`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_crossref_date_normalization.py:319`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_chembl_compound_record.py:15`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_chembl_cell_line.py:13`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_chembl_activity.py:13`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/integration/pipelines/test_chembl_target_component.py:15`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/e2e/test_full_pipeline.py:40`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/e2e/test_full_pipeline.py:139`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/e2e/test_full_pipeline.py:219`)
- **AP-002**: Direct structlog import outside infrastructure layer. Use UnifiedLogger instead. (`tests/e2e/test_full_pipeline.py:310`)

## Cross-subzone Observations
- Architectural integrity is generally well maintained across subzones.

## Top 5 Recommendations
1. Address all high and critical issues flagged in the sub-reports immediately.
