______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-23'

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
- Source commit: `281a0ed48ad70bb108fb90ada50a6a6cdd77f409`
- Source run id: `local-current-main-telemetry-20260623`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-06-23T09:51:39.091871+00:00`

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `92.81%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `8507`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `42.785` | `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage::test_checkpoint_compatibility_runtime_facade_is_not_used_in_tests` | `S7-crosscutting-architecture-a2.xml` |
| 2 | `28.12` | `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage::test_checkpoint_compatibility_runtime_facade_is_not_used_in_src` | `S7-crosscutting-architecture-a2.xml` |
| 3 | `24.051` | `tests.architecture.test_config_discrepancy_metrics_ratchets::test_config_discrepancy_baseline_matches_live_generator` | `S7-crosscutting-architecture-a2.xml` |
| 4 | `23.018` | `tests.architecture.test_config_discrepancy_report_drift::test_config_discrepancy_report_matches_deterministic_generator` | `S7-crosscutting-architecture-a2.xml` |
| 5 | `21.493` | `tests.unit.composition.runtime_builders.test_runner_builder_runtime_modes::test_build_pipeline_runner_uses_configured_mode_outside_test_mode` | `S2-comp-iface.xml` |
| 6 | `16.084` | `tests.architecture.test_cli_command_import_guards::test_non_cli_source_keeps_retained_public_cli_seams_outside_runtime_code` | `S7-crosscutting-architecture-a2.xml` |
| 7 | `15.28` | `tests.architecture.test_config_root_governance::test_runtime_config_discovery_does_not_use_source_parent_arithmetic` | `S7-crosscutting-architecture-a2.xml` |
| 8 | `14.498` | `tests.architecture.test_cli_command_import_guards::test_non_cli_source_avoids_interfaces_package_root_convenience_imports` | `S7-crosscutting-architecture-a2.xml` |
| 9 | `14.129` | `tests.architecture.test_adr_enforcement_matrix::test_adr_enforcement_matrix_artifact_matches_live_generator` | `S7-crosscutting-architecture-a.xml` |
| 10 | `13.15` | `tests.architecture.test_add_svg_text_fallback::test_build_fallback_text_emits_multiline_tspans` | `S7-crosscutting-architecture-a.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage` | 2 | 70.905 | 42.785 |
| 2 | `tests.architecture.test_config_discrepancy_metrics_ratchets` | 2 | 35.379 | 24.051 |
| 3 | `tests.architecture.test_cli_command_import_guards` | 2 | 30.582 | 16.084 |
| 4 | `tests.architecture.test_config_discrepancy_report_drift` | 1 | 23.018 | 23.018 |
| 5 | `tests.unit.composition.runtime_builders.test_runner_builder_runtime_modes` | 1 | 21.493 | 21.493 |
| 6 | `tests.architecture.test_config_root_governance` | 1 | 15.28 | 15.28 |
| 7 | `tests.architecture.test_adr_enforcement_matrix` | 1 | 14.129 | 14.129 |
| 8 | `tests.architecture.test_add_svg_text_fallback` | 1 | 13.15 | 13.15 |
| 9 | `tests.architecture.test_compatibility_freeze_guards` | 1 | 12.274 | 12.274 |
| 10 | `tests.architecture.test_config_surface_entity_residual_plateau` | 2 | 11.72 | 7.029 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
