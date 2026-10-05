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
- Source commit: `d57aae4056ac05458ecf12658433169e23583995`
- Source run id: `local-rf023-coverage-d57aae40-utf8`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `3b59eddc3fbf895ef4b48d4a635f51fdab3a65f571bf3148343f3ed8c83784f5`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-05T20:02:47.818110+00:00`

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
| 1 | `72.888` | `tests.integration.test_dashboard_ux_report_freshness::test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link` | `integration.xml` |
| 2 | `52.714` | `tests.unit.composition.test_workflow_cohort_lineage::test_real_gold_expiry_descendant_and_partial_resume_keep_scoped_history[None]` | `unit-other.xml` |
| 3 | `50.7` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 4 | `47.011` | `tests.contract.schemas.test_pubchem_shard_validation::test_pubchem_identity_shard_accepts_minimal_valid_row` | `contract-confidence.xml` |
| 5 | `36.019` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | `27.549` | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 7 | `20.014` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 8 | `17.328` | `tests.unit.composition.runtime_builders.test_runner_builder_profiles::test_build_pipeline_runner_persists_manifest_before_empty_cached_bronze_fail` | `unit-other.xml` |
| 9 | `12.624` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 10 | `12.424` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.test_dashboard_ux_report_freshness` | 1 | 72.888 | 72.888 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 58.706 | 36.019 |
| 3 | `tests.unit.composition.test_workflow_cohort_lineage` | 1 | 52.714 | 52.714 |
| 4 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 50.7 | 50.7 |
| 5 | `tests.contract.schemas.test_pubchem_shard_validation` | 1 | 47.011 | 47.011 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 3 | 36.683 | 12.624 |
| 7 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 1 | 27.549 | 27.549 |
| 8 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.191 | 11.172 |
| 9 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.014 | 20.014 |
| 10 | `tests.unit.composition.runtime_builders.test_runner_builder_profiles` | 1 | 17.328 | 17.328 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
