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

- Source branch: `codex/pipeline-green-gates-rf022-snapshot-fix`
- Source commit: `d2130e8e6a03a6fd8d60078a26b8ff0019d3a8e7`
- Source run id: `local-rf023-coverage-d2130e8e-retry`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `0c90859e476375c405d84b5eb16449055de4b8c6187929943f5c2a05f803cbf1`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-05T17:55:03.445424+00:00`

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

- Total collected test cases: `32979`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `88.273` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | `20.013` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 3 | `18.801` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | `12.681` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 5 | `11.777` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 6 | `11.642` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 7 | `11.176` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | `10.841` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 9 | `10.808` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 10 | `10.731` | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 88.273 | 88.273 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 40.691 | 18.801 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 25.219 | 10.535 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.649 | 10.841 |
| 5 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.013 | 20.013 |
| 6 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 12.681 | 12.681 |
| 7 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 11.777 | 11.777 |
| 8 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.176 | 11.176 |
| 9 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.731 | 10.731 |
| 10 | `tests.contract.test_provider_contract_drift_replay` | 1 | 10.001 | 10.001 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
