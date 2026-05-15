# Semantic Pipeline Residual Backlog

Generated: `2026-05-15`

## Summary

- Blocking tasks: `0`
- Pair rows: `3248`
- Clusters: `287`
- Risk counts: `{"LOW": 3248}`
- Semantic status counts: `{"CONFLICTING": 20, "EXACT": 2722, "PARTIAL": 67, "WEAK": 439}`
- Normalization counts: `{"COMPATIBLE": 900, "IDENTICAL": 2348}`
- Validation counts: `{"COMPATIBLE": 1053, "IDENTICAL": 2195}`
- Typing counts: `{"COMPATIBLE": 664, "IDENTICAL": 2584}`

## Tasks

| ID | Priority | Status | Rows | Expiry | Gate |
| --- | --- | --- | ---: | --- | --- |
| semantic_drift_budget | P0 | closed | 0 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| hard_status_mismatch_budget | P0 | closed | 0 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| partial_identity_policy_review | P2 | reviewed_until_expiry | 67 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| weak_same_name_inventory_review | P2 | reviewed_until_expiry | 439 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| generic_collision_inventory_review | P2 | reviewed_until_expiry | 20 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-generic-field-ownership --check --json` |
| compatible_normalization_ratchet | P2 | ratcheted | 900 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_validation_ratchet | P2 | ratcheted | 1053 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_typing_ratchet | P2 | ratcheted | 664 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| base_config_semantic_coverage | P2 | closed | 286 |  | `uv run pytest tests/integration/config/test_semantic_pair_matrix_budget.py -q --tb=short` |
