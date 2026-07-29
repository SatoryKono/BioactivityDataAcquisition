______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-29'

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
- Source commit: `pending`
- Source run id: `pending`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-07-29T12:03:59.632345+00:00`

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `95.38%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `23360`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `192.078` | `tests.architecture.test_naming_ambiguity_classifier::test_build_ambiguity_groups_is_deterministic` | `S7-crosscutting-architecture-c.xml` |
| 2 | `76.218` | `tests.architecture.test_provider_registry_decomposition::test_private_default_registry_module_imports_stay_confined_to_sanctioned_seams` | `S7-crosscutting-architecture-c.xml` |
| 3 | `64.276` | `tests.architecture.test_debt_governance_telemetry_reporting::test_debt_governance_snapshot_matches_live_sources` | `S7-crosscutting-architecture-a3.xml` |
| 4 | `55.574` | `tests.architecture.test_provider_registry_decomposition::test_default_provider_registry_raw_calls_stay_confined_to_known_src_baseline` | `S7-crosscutting-architecture-c.xml` |
| 5 | `40.649` | `tests.architecture.test_quality_exemptions_registry::test_exemption_registry_targets_are_live` | `S7-crosscutting-architecture-c.xml` |
| 6 | `38.963` | `tests.architecture.test_naming_ambiguity_classifier::test_build_ambiguity_groups_reports_expected_ok_families` | `S7-crosscutting-architecture-c.xml` |
| 7 | `37.074` | `tests.architecture.test_mounted_worktree_skip_policy::test_tests_do_not_reintroduce_hardcoded_network_drive_skips` | `S7-crosscutting-architecture-c.xml` |
| 8 | `35.843` | `tests.architecture.test_private_module_imports::test_owner_aware_private_module_imports` | `S7-crosscutting-architecture-c.xml` |
| 9 | `35.412` | `tests.architecture.test_import_graph_invariants::test_import_graph_respects_layer_matrix` | `S7-crosscutting-architecture-b.xml` |
| 10 | `34.348` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `S8-crosscutting-governance.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.architecture.test_naming_ambiguity_classifier` | 2 | 231.041 | 192.078 |
| 2 | `tests.architecture.test_provider_registry_decomposition` | 2 | 131.792 | 76.218 |
| 3 | `tests.architecture.test_quality_exemptions_registry` | 2 | 69.7 | 40.649 |
| 4 | `tests.architecture.test_debt_governance_telemetry_reporting` | 1 | 64.276 | 64.276 |
| 5 | `tests.architecture.test_vcr_metadata_catalog_drift` | 2 | 59.262 | 33.691 |
| 6 | `tests.architecture.test_mounted_worktree_skip_policy` | 1 | 37.074 | 37.074 |
| 7 | `tests.architecture.test_private_module_imports` | 1 | 35.843 | 35.843 |
| 8 | `tests.architecture.test_import_graph_invariants` | 1 | 35.412 | 35.412 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 34.348 | 34.348 |
| 10 | `tests.architecture.test_tech_debt_issues_5670_5675_closeout` | 1 | 31.733 | 31.733 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
