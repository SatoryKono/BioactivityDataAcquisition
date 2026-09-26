# Iteration 3 — compatibility and retired aliases

## Evidence

- `configs/quality/config_compatibility_registry.yaml:88-164` records provider
  pagination aliases, root `source.batch_size`, inline source transport
  overrides, pipeline file aliases, and composite
  `merge.column_groups_file` as rejected.
- `tests/architecture/test_config_schema_migration_status.py`,
  `test_config_transition_registry.py`, `test_config_strict_keys.py`, and
  `test_config_ci_invariants.py` passed.
- Apparent `batch_size` and `retry` text occurrences were inspected in context:
  current pipeline batch size, provider pagination batch size, and composite
  execution retry are canonical; retired source-root and provider runtime
  leaves are absent.

## Result

PASS. Retired shapes remain fail-closed; validation was not weakened.
Delta: unchanged. Debt effect: unchanged.
