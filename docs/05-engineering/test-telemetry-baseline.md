______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-14'

______________________________________________________________________

# Test Telemetry Baseline

Committed baseline for CI coverage and slow-test telemetry so engineering
audits do not depend only on ephemeral GitHub artifact retention.
This baseline is the committed evidence companion for the live CI hard gate
`coverage-verify`; historical `test-health` rollups remain non-blocking
trend evidence only.

## Current Authoritative Baseline

- Merge-blocking truth comes from live CI status and `coverage-verify`.
- This document preserves the committed baseline snapshot so audits do not
  rely only on expiring workflow artifacts.

## Baseline Snapshot

- Source branch: `main`
- Source commit: `52353e5e833ce815c0d6c3a581405ce80f488471`
- Source run id: `22890216064`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-05-14T18:12:42.833385+00:00`

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `92.81%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `14859`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `19.186` | `tests.architecture.test_regression_metrics::test_mypy_error_count` | `junit_parallel.xml` |
| 2 | `15.867` | `tests.architecture.test_antipatterns::test_no_hardcoded_secrets` | `junit_parallel.xml` |
| 3 | `5.741` | `tests.unit.interfaces.cli.test_cli_main_module.TestCliMainModule::test_module_runnable_with_help` | `junit_parallel.xml` |
| 4 | `4.541` | `tests.unit.infrastructure.validation.test_pandera_validator.TestPanderaValidatorPropertyBased::test_noop_validators_always_return_valid` | `junit_parallel.xml` |
| 5 | `4.29` | `tests.architecture.test_test_structural_debt::test_no_test_functions_over_200_loc` | `junit_parallel.xml` |
| 6 | `4.204` | `tests.architecture.test_layer_dependencies::test_dead_code_vulture` | `junit_parallel.xml` |
| 7 | `4.108` | `tests.architecture.test_scripts_lifecycle_registry::test_scripts_lifecycle_registry_check_passes` | `junit_parallel.xml` |
| 8 | `4.051` | `tests.architecture.test_scripts_deprecation_backlog::test_scripts_deprecation_report_generation` | `junit_parallel.xml` |
| 9 | `3.948` | `tests.architecture.test_scripts_inventory_manifest::test_scripts_inventory_manifest_drift_check_passes` | `junit_parallel.xml` |
| 10 | `3.757` | `tests.architecture.test_antipatterns::test_no_blocking_io_in_async` | `junit_parallel.xml` |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated YAML and Markdown baseline together.
