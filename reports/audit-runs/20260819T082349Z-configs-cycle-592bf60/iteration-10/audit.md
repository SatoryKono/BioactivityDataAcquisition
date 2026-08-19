# Iteration 10 — generated artifacts and regression automation

## Evidence

The broad architecture sweep reproduced one deterministic failure:

`tests/architecture/test_config_discrepancy_report_drift.py:32` reported that
`docs/04-reference/config_comparison_matrix.csv` did not match
`python -m scripts.schema generate-config-matrix --check`.

The canonical generator was executed with `--update`. It changed only:

- `docs/04-reference/config_comparison_matrix.csv` (four current-config rows);
- `reports/quality/config-discrepancy-baseline.json` (snapshot date).

The generated report itself was already current. Post-fix `--check`, the focused
drift test, final broad architecture `-k "config or schema or dq"` sweep,
`validate-configs`, `check-invariants`, and `git diff --check` pass. The broad
sweep reports three expected WSL filesystem-performance skips.

## Result

FAIL → FIXED. Finding `CFG-001` is resolved in-run. Config discrepancy counts
remain zero and quality/debt budgets remain flat.
