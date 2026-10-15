______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-15'

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

- Source branch: `fix/ci-pr12204`
- Source commit: `3bb4a9fca5636f2bda77a4730090d10ffe07650a`
- Source run id: `local-pr12204-combined-3bb4a9fc`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `1cc9ebaaae57b64299dc6107de1c422b3d13fe5e03df2e84810aa49c3993156b`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-14T16:46:51.736643+00:00`

## Branch-accurate provenance (#5729)

- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,
  `pyproject.toml`, `configs/quality/test_matrix.yaml`,
  `.github/workflows/tests.yml`, and the live JUnit producer
  `scripts/engineering/ci/junit_duration_summary.py`.
- `measurement_provenance.head` and `test_tree_sha256` retain the captured
  run identity when the current audited test tree advances later.
- Freshness uses live UTC (injectable via `BIOETL_TELEMETRY_REFERENCE_NOW`)
  and rejects future/stale `refreshed_at_utc` values.
- `source_commit` must remain an ancestor of HEAD or have a reviewed squash
  bridge in `reports/test-telemetry/squash-provenance.json`. A bridge keeps
  the real captured source/run and requires equal PR/merge trees, source
  ancestry in the PR, merge ancestry in HEAD and unchanged runtime/test inputs.
- Reviewed squash receipts retain hash-verified Git commit/tree objects
  for offline validation when old PR commits are absent from a fresh clone.
  If a shallow checkout's HEAD is newer than the squash merge, unshallow
  it first so merge ancestry and the merged tree can be verified locally.
- To produce a receipt for an existing local capture, run
  `python -m scripts.engineering.ci.test_telemetry_provenance --measurement-repo-root
  <original-worktree> --local-manifest <manifest.json> --pull-request <merged-PR>`.
  The generator validates the complete 17-shard capture and reads the merged
  PR mapping before writing the bridge. Keep the original capture available.
- For a reviewed local coverage capture, run
  `python -m scripts.engineering.ci.update_test_telemetry_baseline
  --rebind-current-tree`, then the coupled `refresh-ci-drift-families`
  update/check for test-gov, flaky-fingerprint, telemetry and evidence.
  Non-local captures require regeneration from their source artifacts.
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
- Actual coverage: `99.66%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total executed test cases: `33963`
- Executed means observed non-skipped JUnit testcase records, not
  collection count or distinct logical tests. Error records can describe
  setup or collection failures rather than a test body run.
- Only measured positive durations enter the slowest-test ranking.
  Older CI timed-row totals are not directly comparable with this count.
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `36.754` | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 2 | `33.633` | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 3 | `23.594` | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 4 | `20.771` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | `12.614` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | `12.328` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 7 | `11.564` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | `11.284` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 9 | `11.197` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 10 | `11.17` | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[None]` | `unit-scripts-tooling-other.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 45.713 | 20.771 |
| 2 | `tests.integration.test_runtime_metric_emission_consistency` | 1 | 36.754 | 36.754 |
| 3 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 1 | 33.633 | 33.633 |
| 4 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 23.594 | 23.594 |
| 5 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.782 | 10.973 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.564 | 11.564 |
| 7 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 11.284 | 11.284 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.197 | 11.197 |
| 9 | `tests.unit.scripts.ops.observability.test_green_acceptance` | 1 | 11.17 | 11.17 |
| 10 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 11.023 | 11.023 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. A legacy JSON timed-row count requires raw `--junit` inputs for the complete recorded source inventory; the updater rejects a partial or legacy-only refresh before writing outputs.
5. Commit the updated baseline and branch-consumable telemetry summary layer together.
