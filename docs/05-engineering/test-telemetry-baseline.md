______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-26'

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
- Source commit: `5b19ac248cf6f8ab4a3554cf62eaf2547a23ff11`
- Source run id: `32935853676`
- Source tree sha256: `67ced9f3d23027f72ea632218bcc686c871000e6204926ebd5ffa812f0c8140a`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-08-26T06:59:26.524018+00:00`

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
- Actual coverage: `96.44%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `49169`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `21.321` | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | `12.364` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 3 | `11.015` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 4 | `10.962` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 5 | `9.315` | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 6 | `7.505` | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 7 | `7.427` | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `junit.unit-other.xml` |
| 8 | `7.333` | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.xml` |
| 9 | `6.335` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 10 | `6.004` | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 4 | 48.631 | 21.321 |
| 2 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.354 | 4.199 |
| 3 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 3 | 12.165 | 4.141 |
| 4 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.962 | 10.962 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.315 | 9.315 |
| 6 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.505 | 7.505 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity` | 1 | 7.427 | 7.427 |
| 8 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.333 | 7.333 |
| 9 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.335 | 6.335 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.004 | 6.004 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
