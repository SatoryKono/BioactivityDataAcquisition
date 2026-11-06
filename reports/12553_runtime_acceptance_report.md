# 12553 Runtime Acceptance Report

## Status

`diagnostics.metric_inventory.reentrant-lock` stays `NOT_RUN_12553` in the
external-resource inventory.

`scripts/engineering/qa/external_resource_inventory.py` accepts only
`runtime_result = NOT_RUN_12553`.
`tests/unit/scripts/engineering/qa/test_external_resource_inventory.py::test_runtime_pass_cannot_be_invented`
locks that rule. Issue #12553 forbids turning a missing or mock-only
observation into `PASS` and forbids weakening the check.

## Observation

`tests/unit/infrastructure/observability/metric_inventory/test_lifecycle_reentrant_lock.py`
calls `collect_metric_inventory` with `_collect_metric_inventory_impl` replaced.
The reentrant lock is held during the call and released on a normal return and
on `ValueError`. The inner inventory scan is not executed. Cancellation,
timeout, and retry are not observed. The other inventory resources are not
observed.

This note does not close #12553.
