# Observability emission assertion inventory

Issue #8340

- Files with observability assertions: **100**
- Critical path candidates: **43**

Domain tests assert via MetricsPort fakes, not Prometheus client.

## Critical path sample

- tests/integration/test_runner_lifecycle.py
- tests/integration/workflow/test_workflow_runner_service.py
- tests/unit/application/composite/checkpoint/test_checkpoint_service.py
- tests/unit/application/composite/runner_pkg/test_runner_observability_mixin.py
- tests/unit/application/composite/runner_pkg/test_runner_runtime_helpers.py
- tests/unit/application/composite/runner_pkg/test_runner_stage_dependency_state_flow.py
- tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py
- tests/unit/application/composite/test_runner.py
- tests/unit/application/composite/test_runner_observability_mixin.py
- tests/unit/application/core/test_batch_checkpoint_recovery_service.py
- tests/unit/application/core/test_batch_checkpoint_recovery_service.py
- tests/unit/application/core/test_batch_execution_lifecycle.py
- tests/unit/application/core/test_batch_execution_lifecycle.py
- tests/unit/application/core/test_batch_executor.py
- tests/unit/application/core/test_batch_executor.py

