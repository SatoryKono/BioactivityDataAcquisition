# Semantic Pipeline Residual Backlog

Generated: `2026-05-15`

## Summary

- Blocking tasks: `0`
- Pair rows: `3233`
- Clusters: `282`
- Risk counts: `{"LOW": 3233}`
- Semantic status counts: `{"EXACT": 2846, "PARTIAL": 68, "WEAK": 319}`
- Normalization counts: `{"COMPATIBLE": 886, "IDENTICAL": 2347}`
- Validation counts: `{"COMPATIBLE": 1039, "IDENTICAL": 2194}`
- Typing counts: `{"COMPATIBLE": 654, "IDENTICAL": 2579}`

## Tasks

| ID | Priority | Status | Rows | Expiry | Gate |
| --- | --- | --- | ---: | --- | --- |
| semantic_drift_budget | P0 | closed | 0 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| hard_status_mismatch_budget | P0 | closed | 0 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| partial_identity_policy_review | P2 | reviewed_until_expiry | 68 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| weak_same_name_inventory_review | P2 | reviewed_until_expiry | 319 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| generic_collision_inventory_review | P2 | reviewed_until_expiry | 0 |  | `uv run python -m scripts.engineering.qa check-generic-field-ownership --check --json` |
| compatible_normalization_ratchet | P2 | ratcheted | 886 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_validation_ratchet | P2 | ratcheted | 1039 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_typing_ratchet | P2 | ratcheted | 654 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| base_config_semantic_coverage | P2 | closed | 286 |  | `uv run pytest tests/integration/config/test_semantic_pair_matrix_budget.py -q --tb=short` |
