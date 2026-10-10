______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-10'

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

- Source branch: `HEAD`
- Source commit: `1bfc36a0c6bf9cbd101e1e8e8bc82bbb03a33cba`
- Source run id: `local-pr12131-final-1bfc36a-w2`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `3fd6bbdc9324b8c41ebb95db8613e47ec5cde3aec66dc04b4ad444c66166ab46`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-10T11:26:51.088638+00:00`

## Branch-accurate provenance (#5729)

- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,
  `pyproject.toml`, `configs/quality/test_matrix.yaml`, and
  `.github/workflows/tests.yml`.
- Freshness uses live UTC (injectable via `BIOETL_TELEMETRY_REFERENCE_NOW`)
  and rejects future/stale `refreshed_at_utc` values.
- `source_commit` must remain an ancestor of HEAD or have a reviewed squash
  bridge in `reports/test-telemetry/squash-provenance.json`. A bridge keeps
  the real captured source/run and requires equal PR/merge trees, source
  ancestry in the PR, merge ancestry in HEAD and unchanged runtime/test inputs.
- New captures use `verification_mode: live_github`: resolve the recorded
  PR's actual merge with read-only GitHub GETs after squash. Never stamp a
  future merge SHA. API failure, unmerged PRs, changed inputs and incomplete
  compare responses fail closed; the live fingerprint/freshness guards remain.
- Reviewed snapshots retain `local_single_host` trust; they are not signed
  vendor attestations or CI execution receipts. Exact `source_commit == HEAD`
  remains opt-in via `BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD=1`.
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
- Actual coverage: `99.67%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `33495`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `26.518` | `tests.unit.scripts.engineering.qa.test_proof_or_stop::test_full_suite_wrapper_is_fail_closed[different_lane]` | `unit-scripts-tooling-other.xml` |
| 2 | `20.019` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 3 | `16.199` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | `15.42` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 5 | `15.127` | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 6 | `11.154` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 7 | `11.113` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | `10.74` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 9 | `10.738` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 10 | `10.511` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 34.955 | 16.199 |
| 2 | `tests.unit.scripts.engineering.qa.test_proof_or_stop` | 1 | 26.518 | 26.518 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.478 | 10.74 |
| 4 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.019 | 20.019 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 16.237 | 10.511 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 2 | 15.943 | 8.485 |
| 7 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 15.42 | 15.42 |
| 8 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 15.127 | 15.127 |
| 9 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.154 | 11.154 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.113 | 11.113 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
