______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-05'

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

- Source branch: `codex/config-root-main-acceptance-20261005`
- Source commit: `090d7a74c56e9de8db2f96d9a183a9058a55ccc8`
- Source run id: `local-full-coverage-wave-46`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `89fd40d116eb824b6430cc0d89cd0baf88c3edda4d18677c79d06491e70f60da`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-05T07:56:40.060186+00:00`

## Branch-accurate provenance (#5729)

- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,
  `pyproject.toml`, `configs/quality/test_matrix.yaml`, and
  `.github/workflows/tests.yml`.
- Freshness uses live UTC (injectable via `BIOETL_TELEMETRY_REFERENCE_NOW`)
  and rejects future/stale `refreshed_at_utc` values.
- `source_commit` must remain an ancestor of HEAD; exact `source_commit == HEAD`
  is opt-in via `BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD=1`.
- GitHub evidence from a non-main branch requires `pull_request`;
  its run URL and id remain independently auditable.
- `--local-manifest <path>` accepts only a complete canonical 17-shard run
  with matching source/test hashes, reachable commit, XML/JUnit digests,
  zero failures/errors and both 85% gates passed. Identity and inputs
  are derived from that manifest; cached CI summaries are never reused.
- Local captures use `source_event: local_coverage_verify`, a `local-` run
  id and no GitHub run URL. Trust remains `local_single_host`;
  `CI=BLOCKED_EXTERNAL_PERMANENT` never becomes CI PASS or lifecycle ADMIT.
- Refresh command:
  `python -m scripts.engineering.ci.update_test_telemetry_baseline`
  `--source-commit <sha> --source-run-id <run-id>`
  `--source-event <event> --source-run-url <url>`.

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `99.70%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `32830`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `87.023` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | `26.372` | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager::test_post_start_source_gate_failure_cannot_report_success` | `repo-backed-unit-ops.xml` |
| 3 | `20.009` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 4 | `19.218` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | `16.16` | `tests.contract.test_composite_merge_golden::test_composite_merge_golden_seed_priority_is_stable` | `contract-confidence.xml` |
| 6 | `15.882` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 7 | `15.365` | `tests.unit.repo_backed.scripts.diagrams.test_generate_pipeline_dataflows::test_ir_resolves_effective_chembl_activity_policy` | `repo-backed-unit-tooling.xml` |
| 8 | `14.298` | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 9 | `13.963` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | `13.799` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 87.023 | 87.023 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 40.856 | 19.218 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager` | 1 | 26.372 | 26.372 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.736 | 11.457 |
| 5 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.009 | 20.009 |
| 6 | `tests.contract.test_composite_merge_golden` | 1 | 16.16 | 16.16 |
| 7 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 15.882 | 15.882 |
| 8 | `tests.unit.repo_backed.scripts.diagrams.test_generate_pipeline_dataflows` | 1 | 15.365 | 15.365 |
| 9 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 14.298 | 14.298 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 13.963 | 13.963 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
