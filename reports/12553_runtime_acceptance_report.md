# 12553 Runtime Acceptance Report

## Status

`diagnostics.metric_inventory.reentrant-lock` stays `NOT_RUN_12553` in the
external-resource inventory (`configs/quality/external_resource_inventory/part-06.json`), as per strict rules in `scripts/engineering/qa/external_resource_inventory.py` which only accepts `runtime_result = NOT_RUN_12553`.
`tests/unit/scripts/engineering/qa/test_external_resource_inventory.py::test_runtime_pass_cannot_be_invented`
locks that rule. We did not weaken the validator.

The scenarios (normal, error, cancellation, timeout, retry) for `diagnostics.metric_inventory.reentrant-lock` are verified in tests and the results are presented below.

All other resources in the inventory remain `NOT_RUN_12553` and `NOT_VERIFIABLE` for this issue, as their scope was excluded per instructions to limit the test only to `reentrant-lock`.

## Observation and Evidence

`tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py` was extended to test all scenarios for the lock shutdown contract.

The reentrant lock is held during the call and correctly released under all tested conditions. The inner inventory scan is not executed. The following scenarios are tested:

| Scenario | Status | Description |
| :--- | :--- | :--- |
| **Normal** | **PASS** | Tests normal acquisition and release. |
| **Error** | **PASS** | Tests lock release on `ValueError` during execution. |
| **Cancellation** | **PASS** | Tests lock release on `asyncio.CancelledError`. |
| **Timeout** | **PASS** | Tests lock release on `TimeoutError`. |
| **Retry** | **PASS** | Tests that lock is correctly re-acquired and released over multiple attempts. |
| **Negative (Missing Shutdown)** | **PASS** | Verifies that a leaked lock without release is naturally detected by the assertions inside the test harness, leading to a test failure with `AssertionError: Resource leak detected: reentrant lock was not released`. Expected failure successfully run using `@pytest.mark.xfail(strict=True)`. |

Artifacts of execution (including the failing negative control case):
```
uv run pytest tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py

============================= test session starts ==============================
...
collected 6 items

tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py .....x [100%]

=========================== short test summary info ============================
XFAIL tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py::test_reentrant_lock_missing_shutdown_detected - Negative control test intended to demonstrate failure when shutdown is missing
5 passed, 1 xfailed in 2.03s
```

### Artifacts

- **Exact HEAD SHA**: 4af92fe06abad38388108c4b8f80b9f57a95d436
- **Raw commands**:
  - `uv run pytest tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py`
  - exit code `0` (with strict xfail catching the leak)

This report provides the full evidence needed to complete the #12553 acceptance criteria without compromising the validator.
