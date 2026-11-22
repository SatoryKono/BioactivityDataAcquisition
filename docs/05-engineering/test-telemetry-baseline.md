______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-11-22'

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
- Source commit: `990793a7b506ef4baa42f7d450f8242e52d1cf8f`
- Source run id: `local-local-coverage-pr13241-v3`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `53d23face27ad539910bce79412e8362767044db941762142b8adf22d2b82686`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-11-22T17:18:50.253475+00:00`

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
  a manually dispatched Nightly run may instead use `workflow_dispatch`.
  Its run URL and id remain independently auditable.
- Use `workflow_dispatch` only for a manually started `Nightly` run on the
  PR branch. Start it with `gh workflow run nightly.yml --ref <branch>`,
  then download both source artifacts from that exact run:
  `gh run download <run-id> --name coverage-report --dir reports` and
  `gh run download <run-id> --name test-duration-telemetry
  --dir reports/test-telemetry`. Confirm the run's head SHA and use it
  as `--source-commit`; keep `--source-event workflow_dispatch` and the
  matching `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/<run-id>` URL.
- `--local-manifest <path>` accepts only a complete canonical 17-shard run
  with matching source/test hashes, reachable commit, XML/JUnit digests,
  zero failures/errors and both 85% gates passed. Identity and inputs
  are derived from that manifest; cached CI summaries are never reused.
- Local captures use `source_event: local_coverage_verify`, a `local-` run
  id and no GitHub run URL. Trust remains `local_single_host`;
  `CI=BLOCKED_EXTERNAL_PERMANENT` never becomes CI PASS or lifecycle ADMIT.
- Refresh a non-local capture with its recorded identity:
  `python -m scripts.engineering.ci.update_test_telemetry_baseline
  --coverage-xml reports/coverage/coverage.xml
  --slowest-json reports/test-telemetry/slowest-tests.json
  --source-branch <branch> --source-commit <sha>
  --source-run-id <run-id> --source-event <event>
  --source-run-url <url>`. Use `workflow_dispatch` only for the
  manually started Nightly workflow described above.

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `99.51%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total executed test cases: `41275`
- Executed means observed non-skipped JUnit testcase records, not
  collection count or distinct logical tests. Error records can describe
  setup or collection failures rather than a test body run.
- Only measured positive durations enter the slowest-test ranking.
  Older CI timed-row totals are not directly comparable with this count.
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `35.725` | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `unit-scripts-tooling-other.xml` |
| 2 | `21.051` | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 3 | `17.994` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | `16.214` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 5 | `14.52` | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 6 | `14.326` | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 7 | `13.395` | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `unit-scripts-tooling-other.xml` |
| 8 | `11.954` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | `11.529` | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected::test_nightly_shadow_changes_keep_both_archive_and_inventory_owners[scripts/engineering/ci/nightly_shadow_archive.py]` | `unit-scripts-tooling-other.xml` |
| 10 | `11.45` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.35 | 17.994 |
| 2 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 35.725 | 35.725 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.051 | 11.175 |
| 4 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 21.051 | 21.051 |
| 5 | `tests.unit.scripts.engineering.ci.test_pr_lane_results` | 2 | 19.492 | 10.527 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 16.214 | 16.214 |
| 7 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 14.52 | 14.52 |
| 8 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 14.326 | 14.326 |
| 9 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 13.395 | 13.395 |
| 10 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected` | 1 | 11.529 | 11.529 |

## Refresh Procedure

1. Download original `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from the same qualified CI run. Verify its exact head, all 17 shards, module nonregression and both hard coverage gates; report the overall workflow separately.
2. If XML expired or measured inputs changed, obtain a new complete measurement. Use a fresh Nightly or a verified `--local-manifest`; logs and supplied percentages cannot replace the original XML.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --coverage-xml <original-xml> --source-commit <full-40-character-sha> --source-run-id <run-id> ...` with matching same-run duration inputs. The CLI rejects percentage overrides and input drift, and retains the XML measurement time instead of stamping the current time.
4. A legacy JSON timed-row count requires raw `--junit` inputs for the complete recorded source inventory; the updater rejects a partial or legacy-only refresh before writing outputs.
5. Commit the updated baseline and branch-consumable telemetry summary layer together.
