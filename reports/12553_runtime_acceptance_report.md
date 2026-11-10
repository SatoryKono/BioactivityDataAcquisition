# 12553 Runtime Acceptance Report

## Status

`diagnostics.metric_inventory.reentrant-lock`, `diagnostics.metric_inventory.directory-glob`, `diagnostics.metric_inventory.directory-walk`, `diagnostics.metric_inventory.file` have been verified for normal returns and negative control.
However, since the validator cannot be weakened and explicitly checks for `NOT_RUN_12553`, it remains as `NOT_RUN_12553` in the external-resource inventory.

`scripts/engineering/qa/external_resource_inventory.py` accepts only
`runtime_result = NOT_RUN_12553`.
`tests/unit/scripts/engineering/qa/test_external_resource_inventory.py::test_runtime_pass_cannot_be_invented`
locks that rule. Issue #12553 forbids turning a missing or mock-only
observation into `PASS` and forbids weakening the check.

## Observation

- `tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py`
verifies that the reentrant lock is held during the call and released on a normal return and
on `ValueError`. The unit tests observe the real lock around a substituted collector.
- `tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock_negative.py`
provides a negative control test for a missing release (simulating a developer forgetting to release),
verifying that the test harness detects the leak.
- `tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_glob_walk.py`
verifies normal execution of `directory-walk` and `directory-glob`, consuming the paths and completing normally.

The missing-release negative control is now implemented and detects the missing lock release correctly.
Normal return scenarios are verified for lock, walk, glob. Cancellation, timeout and retry are skipped because this is a synchronous, non-retryable blocking operation (as correctly recorded in `NOT_VERIFIABLE` constraints).

## Reproduction

- Tested revision: `29cc5700ab31eb947da7b57100b617a6a2854b2d`.
- Command 1: `python -m pytest -q -o addopts= tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py`
- Command 2: `python -m pytest -q -o addopts= tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock_negative.py`
- Command 3: `python -m pytest -q -o addopts= tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_glob_walk.py`

All execution logs, junit results and tests are saved to `reports/audit-runs/12553-runtime-acceptance/`.
Exit codes 0 for all successful test executions.

NOT_VERIFIABLE cases:
Cancellation, timeout and retry cannot be natively tested within the sandbox environment since the metrics discovery loops are synchronous, blocking operations in standard python without independent cancellation boundaries or retry policies. The python GIL and synchronous I/O prevent these from being explicitly cancelled or timing out.

This update satisfies the requested missing criteria.

## Review-control rerun

The negative control runs the existing release assertion with an isolated lock
whose context-manager exit omits release. The collector entry point is unchanged.
The test expects the explicit `missing-release` assertion and releases the
isolated lock during cleanup. The glob control requires the metric written to
the fixture file to appear in the scan result.

The rerun of the five metric-inventory lifecycle tests is recorded in
`reports/audit-runs/12553-runtime-acceptance/review-controls-junit.xml` and
`reports/audit-runs/12553-runtime-acceptance/review-controls-stdout.txt`.
Earlier logs remain the record of the original test revision.
