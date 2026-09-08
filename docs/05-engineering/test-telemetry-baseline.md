______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-08'

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

- Source branch: `codex/operator-runtime-final-cab240`
- Source commit: `c40e53f45c2456266eca4fee42ad7c995a59f01a`
- Source run id: `34271654298`
- Source event: `pull_request`
- Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34271654298`
- Source tree sha256: `a67b4b94fd1d3ddc6e2217f5e4177886b6b5dad06b3f18d99bda90d6bc60922d`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-09-08T20:07:55.324162+00:00`

## Branch-accurate provenance (#5729)

- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,
  `pyproject.toml`, `configs/quality/test_matrix.yaml`, and
  `.github/workflows/tests.yml`.
- Freshness uses live UTC (injectable via `BIOETL_TELEMETRY_REFERENCE_NOW`)
  and rejects future/stale `refreshed_at_utc` values.
- `source_commit` must remain an ancestor of HEAD; exact `source_commit == HEAD`
  is opt-in via `BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD=1`.
- A non-main source branch is accepted only for a `pull_request` run;
  the run URL and id keep that pre-merge evidence independently auditable.
- Refresh command:
  `python -m scripts.engineering.ci.update_test_telemetry_baseline`
  `--source-commit <sha> --source-run-id <run-id>`
  `--source-event <event> --source-run-url <url>`.

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `96.71%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `49970`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `12.65` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | `10.812` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | `9.407` | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 4 | `8.089` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 5 | `7.455` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 6 | `7.415` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 7 | `7.34` | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 8 | `7.249` | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 9 | `6.004` | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 10 | `5.812` | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 27.52 | 12.65 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 16.519 | 10.812 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 13.554 | 8.089 |
| 4 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.519 | 4.239 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.407 | 9.407 |
| 6 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.34 | 7.34 |
| 7 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.249 | 7.249 |
| 8 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.004 | 6.004 |
| 9 | `tests.unit.scripts.docs.passports.test_passport_projector` | 1 | 5.812 | 5.812 |
| 10 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency` | 1 | 5.325 | 5.325 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
