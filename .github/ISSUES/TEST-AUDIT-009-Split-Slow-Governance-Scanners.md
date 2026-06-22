---
title: "[TEST-AUDIT-009] Split slow governance scanners from fast test feedback lanes"
github_issue: 5493
labels: ci, technical-debt
assignees: []
---

## Context

The current test matrix already has sharded lanes and `xdist`, but the
2026-06-22 audit shows that cold-run latency is still dominated by
architecture/governance tests that spawn external scanners or generator checks.

## Problem

The slow-test telemetry baseline shows the top slow tests are governance/scanner
checks:

- `tests.architecture.test_regression_metrics::test_mypy_error_count` - 19.186s
- `tests.architecture.test_antipatterns::test_no_hardcoded_secrets` - 15.867s
- `tests.architecture.test_test_structural_debt::test_no_test_functions_over_200_loc` - 4.29s
- `tests.architecture.test_layer_dependencies::test_dead_code_vulture` - 4.204s
- `tests.architecture.test_scripts_lifecycle_registry::test_scripts_lifecycle_registry_check_passes` - 4.108s
- `tests.architecture.test_scripts_deprecation_backlog::test_scripts_deprecation_report_generation` - 4.051s
- `tests.architecture.test_scripts_inventory_manifest::test_scripts_inventory_manifest_drift_check_passes` - 3.948s

## Evidence

- `configs/quality/test_telemetry_baseline.yaml`
- `reports/test-telemetry/slowest-tests.md`
- `tests/architecture/test_regression_metrics.py`
- `tests/architecture/test_antipatterns.py`
- `tests/architecture/test_scripts_inventory_manifest.py`
- `configs/quality/test_matrix.yaml`

## Acceptance Criteria

- [ ] Fast unit and fast architecture boundary lanes do not run repo-wide scanner subprocesses.
- [ ] Slow governance subprocess checks remain CI-visible and merge-blocking where they protect architecture invariants.
- [ ] Test matrix documents the distinction between fast boundary checks and slow governance checks.
- [ ] Slowest-test telemetry shows scanner-heavy tests grouped under the intended lane.
- [ ] No architecture invariant is removed or weakened.

