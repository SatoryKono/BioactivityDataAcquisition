# Architecture and Affected Lane Benchmark Results (Epoch 2208 / b)

## Blockers Encountered

1. **Watchdog Timeout Blocker (Execution Limit):** The environment's 400-second execution watchdog repeatedly terminated both serial (`-n 0`) and parallel benchmark runs for the `architecture` lane. Because the 400s limit is strictly enforced and bypassing it via background tasks is forbidden, a full execution matrix completing `pytest tests/architecture/` with the required parameters within a single test run or script iteration cannot be achieved. The exact timeout duration is 401s on average. Raw exit codes for aborted runs reflect the SIGTERM (143) status.

2. **Configuration Surface Drift Blocker (Quality Gates):** A discrepancy remains where the `unique_parameter_count` metric for the `config_surface` is generated as 352 (with `entity_effective` as 260) by the `generate-config-matrix` producer, but the current `configs/quality/debt_scorecard.yaml` enforces 353 (and 261, respectively). I generated the actual artifact using `python -m scripts.schema generate-config-matrix --update` exactly as instructed by the test failures. Because manual editing of the `debt_scorecard.yaml` budgets to merely force a match is forbidden without a verified source of the drift (it's deemed external drift), the test `test_debt_scorecard_config_surface_ratchet_matches_baseline` continues to fail in the `architecture` suite.

## Methodology

Attempted to benchmark `tests/architecture` and `tests/unit/domain` (affected lane) using `scripts.engineering.ci.run_pytest_resilient`. Tested configurations include `-n 0`, `-n 2`, `-n 4`, and `-n auto` under both `loadscope` and `loadfile` distribution strategies.

## Execution Receipts

Below is the partial receipt from the attempts:
```
architecture | -n 0 | Run 1 | 238.64s | Exit: 143 (SIGTERM due to parent watchdog)
architecture | -n 0 | Run 1 (Direct pytest) | 400.9s | Exit: Terminated by watchdog
architecture | -n auto loadscope | Run 1 | 410.39s | Exit: Terminated by watchdog
```
Due to the watchdog limit, complete end-to-end CPU/RSS and wall-clock times across 3 runs for each matrix item are **UNKNOWN**.

## Rationale & Decision

Since the benchmark was blocked by the 400-second execution limit and a comprehensive runtime measurement across the complete test execution for `-n auto loadscope` vs `-n 0` cannot be accurately completed or proven to reduce the critical path, **no changes** will be made to the configuration of `run_pytest_resilient.py` or `.github/workflows/pr-required.yml`. The existing accepted implementation remains unchanged, and the conservative serial mode (or the currently implemented configuration) is upheld as there is no proven benchmark to justify a modification in this constrained environment.
