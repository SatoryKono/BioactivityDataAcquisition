______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-07'

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

- Source branch: `fix/run-explorer-trust-10174-10191`
- Source commit: `c18f737c3edc439e21ef8eaf2ebb6cd79060d01f`
- Source run id: `34148282491`
- Source event: `pull_request`
- Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34148282491`
- Source tree sha256: `f3856a7ab557152d17c1f8b05a69e796533b952f439948467030a06616199ea0`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-09-07T17:48:00.241959+00:00`

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

- Total collected test cases: `49802`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `13.408` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | `11.013` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | `8.491` | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 4 | `7.957` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 5 | `7.807` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 6 | `7.666` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 7 | `7.329` | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 8 | `7.292` | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 9 | `7.266` | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestRegistryNameUniqueness::test_registry_has_unique_names` | `junit.unit-other.xml` |
| 10 | `7.224` | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 28.881 | 13.408 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 4 | 26.515 | 11.013 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 12.176 | 6.494 |
| 4 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 3 | 11.317 | 3.84 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 8.491 | 8.491 |
| 6 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 2 | 7.637 | 3.891 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.329 | 7.329 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.292 | 7.292 |
| 9 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestRegistryNameUniqueness` | 1 | 7.266 | 7.266 |
| 10 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.224 | 7.224 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
