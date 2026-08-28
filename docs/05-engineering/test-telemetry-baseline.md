______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-28'

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

- Source branch: `fix/ci-actions-main-20260828`
- Source commit: `e331747c4a632e0c616e0bfdb6bcbfafb4a8897d`
- Source run id: `33168461811`
- Source tree sha256: `2a118cbf07c3dc2e667d81829401f5cfe5b45f2b28a8b05651d38d4984e2e7ce`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-08-28T12:15:44.880818+00:00`

## Branch-accurate provenance (#5729)

- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,
  `pyproject.toml`, `configs/quality/test_matrix.yaml`, and
  `.github/workflows/tests.yml`.
- Freshness uses live UTC (injectable via `BIOETL_TELEMETRY_REFERENCE_NOW`)
  and rejects future/stale `refreshed_at_utc` values.
- `source_commit` must remain an ancestor of HEAD; exact `source_commit == HEAD`
  is opt-in via `BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD=1`.
- Refresh command:
  `python -m scripts.engineering.ci.update_test_telemetry_baseline`
  `--source-commit <sha> --source-run-id <run-id>`.

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `96.56%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `49250`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `14.784` | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | `13.094` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.xml` |
| 3 | `10.938` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 4 | `9.247` | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 5 | `8.86` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 6 | `8.707` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 7 | `8.188` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 8 | `7.433` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.xml` |
| 9 | `7.357` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.xml` |
| 10 | `7.306` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_tolerates_unavailable_remote_main_baseline_builder` | `junit-unit-scripts-tooling.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 35.19 | 13.094 |
| 2 | `tests.unit.scripts.docs.passports.test_passport_projector` | 3 | 32.351 | 14.784 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.033 | 8.188 |
| 4 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.166 | 4.062 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.938 | 10.938 |
| 6 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.247 | 9.247 |
| 7 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 2 | 7.726 | 3.934 |
| 8 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 6.911 | 6.911 |
| 9 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.003 | 6.003 |
| 10 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 5.085 | 5.085 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
