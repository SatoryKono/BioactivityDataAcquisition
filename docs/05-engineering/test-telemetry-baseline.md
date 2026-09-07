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

- Source branch: `fix/dashboard-overview-runtime-incident-five`
- Source commit: `d5709c075842b97bce4be7a776b80aca60d8e58e`
- Source run id: `34143259598`
- Source event: `pull_request`
- Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34143259598`
- Source tree sha256: `755d16956e1008675979b2b4518c12f2e41474cbeec55514ffa2e76f6cf3c08c`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-09-07T16:46:12.309477+00:00`

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

- Total collected test cases: `49745`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `17.483` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | `15.272` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 3 | `10.862` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 4 | `10.477` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 5 | `10.406` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 6 | `9.456` | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 7 | `8.055` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 8 | `6.852` | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 9 | `6.618` | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 10 | `6.484` | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 42.228 | 17.483 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 26.134 | 15.272 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.235 | 8.055 |
| 4 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.413 | 4.218 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.456 | 9.456 |
| 6 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 6.852 | 6.852 |
| 7 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 6.618 | 6.618 |
| 8 | `tests.unit.scripts.docs.passports.test_passport_projector` | 1 | 6.484 | 6.484 |
| 9 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration` | 1 | 6.399 | 6.399 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.003 | 6.003 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
