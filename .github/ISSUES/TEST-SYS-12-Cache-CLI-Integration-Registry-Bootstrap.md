---
title: "test(perf): reuse cached immutable registry metadata in CLI integration suites"
labels:
  - testing
  - performance
  - composition
  - priority:P1
---

# Context

CLI integration tests legitimately cross the interfaces/composition boundary,
but several suites repeatedly rebuild global pipeline registration.

Iteration metadata: `CYCLE-01..CYCLE-05`, first observed at
`3910046d2716606019babc2a272bd64dc2d87982`.

# Problem

Autouse fixtures call `register_all_pipelines()` per class/test in:

- `tests/integration/interfaces/test_cli_shutdown_integration.py`
- `tests/integration/interfaces/test_cli_run_incremental.py`
- `tests/integration/interfaces/test_cli_run_dry_run.py`

The repository already provides immutable cached bootstrap metadata and
per-test clones at `tests/conftest.py:889-910`.

Finding fingerprint:
`tests:cli-integration-rebuilds-global-pipeline-registry-per-test`

# Evidence

- Code inspection:
  `test_cli_shutdown_integration.py:51-54,111-115,242-245,315-318`;
  `test_cli_run_incremental.py:34-46,188-191`;
  `test_cli_run_dry_run.py:38-50,261-264`.
- Duration evidence from the current branch: targeted suite passed 37 tests,
  with setup hotspots of 14.15s and 10.51s and a 9.89s call.
- Historical JUnit evidence records roughly 42 seconds across the affected CLI
  groups.

# Root Cause

The tests use the global registration convenience function instead of cloning
the existing session-cached immutable bootstrap model for each isolated test.

# Architecture Impact

The behavior remains in composition, so layering is not violated. The repeated
global wiring increases test cost and mutable-global coupling, limiting safe
parallelism and developer feedback speed.

# Proposed Remediation

Inject `cached_populated_isolated_registry` or an equivalent per-test clone into
the CLI invocation seam. Keep full composition-root construction only in tests
whose purpose is bootstrap wiring.

# Rejected Approaches

- Do not session-scope a mutable global registry.
- Do not mock production registry internals.
- Do not skip slow tests or widen performance budgets.

# Acceptance Criteria

- Each test receives isolated registry state.
- The three suites retain their behavioral assertions.
- Targeted duration materially decreases against the recorded baseline.
- Randomized/order-varied reruns remain green.

# Verification

- Run the three targeted integration modules with `--durations=10`.
- Run related composition and registry isolation tests.
- Run relevant architecture gates and Ruff.

# Risks and Rollback

The main risk is hidden registry mutation leaking between cases. Roll back to
per-test full registration if clone isolation cannot be proven.

# Definition of Done

Targeted suites pass with explicit isolation, duration evidence improves, no
composition-only DI rule is weakened, and technical-debt budgets are unchanged.
