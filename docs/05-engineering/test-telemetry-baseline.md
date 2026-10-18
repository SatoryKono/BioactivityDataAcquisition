______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-17'

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

- Source branch: `fix/cf039-benchmark-caller-12043`
- Source commit: `badcaeb5d30892e9356969342a14403990794201`
- Source run id: `local-bioetl-local-coverage-badcaeb-r2`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `d4931026d12ca026932d44db5025e879ecb6828c07df779355a22109f8f60b9f`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-17T17:29:14.810533+00:00`

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
- Actual coverage: `99.66%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total executed test cases: `34094`
- Executed means observed non-skipped JUnit testcase records, not
  collection count or distinct logical tests. Error records can describe
  setup or collection failures rather than a test body run.
- Only measured positive durations enter the slowest-test ranking.
  Older CI timed-row totals are not directly comparable with this count.
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `208.818` | `tests.unit.scripts.ci.test_update_test_telemetry_baseline::test_legacy_only_refresh_rejects_before_overwriting_baseline` | `unit-scripts-tooling-other.xml` |
| 2 | `93.182` | `tests.unit.scripts.ops.observability.test_green_optional_inputs::test_absent_optional_child_requires_verified_empty_input[None]` | `unit-scripts-tooling-other.xml` |
| 3 | `45.829` | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[None]` | `unit-scripts-tooling-other.xml` |
| 4 | `27.247` | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 5 | `27.237` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 6 | `20.884` | `tests.unit.application.services.dq.test_silver_statistics_helpers.TestSilverStatisticsHelpers::test_profile_categorical_column_builds_top_values` | `unit-application.xml` |
| 7 | `18.436` | `tests.unit.application.services.dq.test_silver_statistics_helpers.TestSilverStatisticsHelpers::test_profile_numeric_column_returns_distribution_for_non_empty_values` | `unit-application.xml` |
| 8 | `18.228` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | `18.133` | `tests.unit.infrastructure.storage.silver_writer.test_silver_writer_lineage.TestSilverWriterCsvExport::test_write_silver_with_csv_exporter` | `unit-filesystem-contracts.xml` |
| 10 | `17.777` | `tests.unit.scripts.ai.test_prompt_library::test_check_registry_ok` | `unit-scripts-tooling-other.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline` | 1 | 208.818 | 208.818 |
| 2 | `tests.unit.scripts.ops.observability.test_green_optional_inputs` | 1 | 93.182 | 93.182 |
| 3 | `tests.unit.scripts.ops.observability.test_green_acceptance` | 1 | 45.829 | 45.829 |
| 4 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.188 | 18.228 |
| 5 | `tests.unit.application.services.dq.test_silver_statistics_helpers.TestSilverStatisticsHelpers` | 2 | 39.32 | 20.884 |
| 6 | `tests.unit.scripts.ops.observability.test_grafana_acceptance_provenance` | 2 | 30.397 | 15.287 |
| 7 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 27.247 | 27.247 |
| 8 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 27.237 | 27.237 |
| 9 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.668 | 10.872 |
| 10 | `tests.unit.infrastructure.storage.silver_writer.test_silver_writer_lineage.TestSilverWriterCsvExport` | 1 | 18.133 | 18.133 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. A legacy JSON timed-row count requires raw `--junit` inputs for the complete recorded source inventory; the updater rejects a partial or legacy-only refresh before writing outputs.
5. Commit the updated baseline and branch-consumable telemetry summary layer together.
