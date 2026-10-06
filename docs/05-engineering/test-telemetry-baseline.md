______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-06'

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

- Source branch: `codex/ci-11929-11931-preparation`
- Source commit: `a63090e110ecf290d7a4d5dc8d84e75e7307ab1a`
- Source run id: `local-coverage`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `a1be027f03352d6ae870f2d54033c7adedf5bca49125905c67265c8158f98dd8`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-06T14:59:22.731141+00:00`

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

- Total collected test cases: `33138`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `20.024` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | `17.203` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | `11.181` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 4 | `11.147` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 5 | `10.756` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 6 | `10.613` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 7 | `10.56` | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 8 | `9.788` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | `9.683` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 10 | `8.286` | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 36.674 | 17.203 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.369 | 10.756 |
| 3 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.024 | 20.024 |
| 4 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.181 | 11.181 |
| 5 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.147 | 11.147 |
| 6 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.56 | 10.56 |
| 7 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 8.286 | 8.286 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.986 | 7.986 |
| 9 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 7.917 | 7.917 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 7.411 | 7.411 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
