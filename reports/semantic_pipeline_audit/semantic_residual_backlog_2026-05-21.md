# Semantic Pipeline Residual Backlog

Generated: `2026-05-21`

## Summary

- Blocking tasks: `0`
- Pair rows: `3129`
- Clusters: `283`
- Risk counts: `{"LOW": 3129}`
- Semantic status counts: `{"EXACT": 2742, "PARTIAL": 68, "WEAK": 319}`
- Normalization counts: `{"COMPATIBLE": 839, "IDENTICAL": 2290}`
- Validation counts: `{"COMPATIBLE": 990, "IDENTICAL": 2139}`
- Typing counts: `{"COMPATIBLE": 618, "IDENTICAL": 2511}`

## Tasks

| ID | Priority | Status | Rows | Expiry | Gate |
| --- | --- | --- | ---: | --- | --- |
| semantic_drift_budget | P0 | closed | 0 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| hard_status_mismatch_budget | P0 | closed | 0 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| partial_identity_policy_review | P2 | reviewed_until_expiry | 68 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| weak_same_name_inventory_review | P2 | reviewed_until_expiry | 319 | 2026-11-15 | `uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json` |
| generic_collision_inventory_review | P2 | reviewed_until_expiry | 0 |  | `uv run python -m scripts.engineering.qa check-generic-field-ownership --check --json` |
| compatible_normalization_ratchet | P2 | ratcheted | 839 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_validation_ratchet | P2 | ratcheted | 990 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| compatible_typing_ratchet | P2 | ratcheted | 618 |  | `uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json` |
| base_config_semantic_coverage | P2 | closed | 328 |  | `uv run pytest tests/integration/config/test_semantic_pair_matrix_budget.py -q --tb=short` |
