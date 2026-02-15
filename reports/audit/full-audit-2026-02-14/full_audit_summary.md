# Full Codebase Audit Summary

- Timestamp (UTC): 2026-02-14 01:35:08
- Total tracked files audited: 1985
- Python source files audited (`src/`): 542
- Python test files indexed (`tests/`): 565
- Entities cataloged (classes/functions/constants/variables/parameters): 18285
- Pipelines in matrix: 21

## Entity Classification
| Classification | Count |
|---|---:|
| ACTIVE | 13850 |
| PRODUCTION_ONLY | 1266 |
| TEST_ONLY | 908 |
| DEAD | 2261 |

## Risk Highlights
- Dead code candidates (non-exempt): 2251
- Duplicate names: 2078
- Duplicate logic groups: 97
- Architecture violations: 266
- Documentation findings: 74

## Output Files
- `files_inventory.csv`
- `entities.csv`
- `entities_pipeline_matrix.csv`
- `dead_code_candidates.csv`
- `duplicate_names.csv`
- `duplicate_logic.csv`
- `architecture_violations.csv`
- `architecture_report.md`
- `documentation_audit_report.md`
- `metadata.json`

## Notes on Method
- The matrix columns for pipelines are generated from `PIPELINE_CONFIGS` in `src/bioetl/composition/factories/pipeline_factories.py`.
- Pipeline usage counts are direct lexical references of entity names inside pipeline scopes (provider files + config-linked symbols + runtime composition files).
- Dead/duplicate classification is static and should be validated against runtime behavior for removals.