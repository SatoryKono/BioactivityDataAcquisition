______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-18'

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

- Source branch: `coderabbit/refresh-test-telemetry-baseline/0ec377e9`
- Source commit: `2fe807fe106f8153f2b3537a5fb22c92b9f4bca2`
- Source run id: `local-pr-12267-ci-baseline`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `bc253de582265376e8ad49a7454602da751f25a371a29f474fdc9616c934141e`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-18T22:19:07.669472+00:00`

## Branch-accurate provenance (#5729)

- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,
  `pyproject.toml`, `configs/quality/test_matrix.yaml`,
  `.github/workflows/tests.yml`, and the live JUnit producers
  `scripts/engineering/ci/junit_duration_summary.py` and
  `scripts/engineering/dev/pytest_junit_subtests.py`.
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
- Actual coverage: `99.57%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total executed test cases: `34483`
- Executed means observed non-skipped JUnit testcase records, not
  collection count or distinct logical tests. Error records can describe
  setup or collection failures rather than a test body run.
- Only measured positive durations enter the slowest-test ranking.
  Older CI timed-row totals are not directly comparable with this count.
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `15.083` | `tests.performance.test_delta_sequential_merge::test_delta_sequential_merge_scaling[100]` | `serial.xml` |
| 2 | `14.43` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | `10.753` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 4 | `10.751` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 5 | `10.517` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 6 | `10.492` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 7 | `10.407` | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 8 | `8.825` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | `8.674` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 10 | `6.561` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 31.929 | 14.43 |
| 2 | `tests.performance.test_delta_sequential_merge` | 2 | 21.554 | 15.083 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.009 | 10.517 |
| 4 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.753 | 10.753 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.751 | 10.751 |
| 6 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.407 | 10.407 |
| 7 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.561 | 6.561 |
| 8 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 6.551 | 6.551 |
| 9 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 6.543 | 6.543 |
| 10 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 6.311 | 6.311 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. A legacy JSON timed-row count requires raw `--junit` inputs for the complete recorded source inventory; the updater rejects a partial or legacy-only refresh before writing outputs.
5. Commit the updated baseline and branch-consumable telemetry summary layer together.
