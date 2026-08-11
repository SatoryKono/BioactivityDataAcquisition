# Semantic Pipeline Residual Backlog

Generated: `2026-07-01`

## Summary

- Blocking tasks: `1`
- Pair rows: `3245`
- Clusters: `290`
- Risk counts: `{"HIGH": 1, "LOW": 3244}`
- Semantic status counts: `{"EXACT": 2742, "PARTIAL": 68, "WEAK": 435}`
- Normalization counts: `{"COMPATIBLE": 887, "IDENTICAL": 2358}`
- Validation counts: `{"COMPATIBLE": 1042, "IDENTICAL": 2203}`
- Typing counts: `{"COMPATIBLE": 663, "CONFLICTING": 1, "IDENTICAL": 2581}`

## Tasks

| ID | Priority | Status | Rows | Expiry | Gate |
| --- | --- | --- | ---: | --- | --- |
| semantic_drift_budget | P0 | closed | 1 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| hard_status_mismatch_budget | P0 | closed | 1 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| partial_identity_policy_review | P2 | reviewed_until_expiry | 68 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| weak_same_name_inventory_review | P2 | reviewed_until_expiry | 435 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| generic_collision_inventory_review | P2 | reviewed_until_expiry | 0 |  | `uv run python -m scripts.engineering.qa check-generic-field-ownership --check --json` |
| compatible_normalization_ratchet | P2 | ratcheted | 887 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_validation_ratchet | P2 | ratcheted | 1042 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_typing_ratchet | P2 | ratcheted | 663 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| base_config_semantic_coverage | P2 | closed | 340 |  | `uv run pytest tests/integration/config/test_semantic_pair_matrix_budget.py -q --tb=short` |
