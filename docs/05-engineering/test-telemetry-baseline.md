______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-06'

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

- Source branch: `master_20260806-6`
- Source commit: `feb052551a2d9aecb103ca8254746fa4a67781d6`
- Source run id: `merge-resolve-8216-20260806`
- Source tree sha256: `2e483519602040c80eda8e28868150727069eb49de977be3042268cefa72e0ea`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-08-06T15:49:32.455406+00:00`

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
- Actual coverage: `95.24%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `46742`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `22.399` | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit.unit-other.xml` |
| 2 | `11.55` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit.unit-other.xml` |
| 3 | `11.315` | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-fast.xml` |
| 4 | `10.797` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit.unit-other.xml` |
| 5 | `10.615` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 6 | `7.251` | `tests.unit.scripts.docs.passports.test_passport_projector::test_generated_facts_validate_against_published_schemas` | `junit.unit-other.xml` |
| 7 | `6.817` | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 8 | `6.505` | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration::test_bootstrapped_service_can_list_pipelines` | `junit.unit-other.xml` |
| 9 | `6.126` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 10 | `5.529` | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit.unit-other.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 12 | 92.986 | 22.399 |
| 2 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 12.275 | 4.111 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.615 | 10.615 |
| 4 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 6.817 | 6.817 |
| 5 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration` | 1 | 6.505 | 6.505 |
| 6 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.126 | 6.126 |
| 7 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 5.529 | 5.529 |
| 8 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 1 | 5.235 | 5.235 |
| 9 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit` | 1 | 5.086 | 5.086 |
| 10 | `tests.unit.scripts.test_normalization_governance_cli_smoke` | 1 | 4.746 | 4.746 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
