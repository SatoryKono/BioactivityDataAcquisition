______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-11-12'

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

- Source branch: `codex/hooks-13038-followup`
- Source commit: `24ba79fe5932b73dee1651c1442e50a5a7c83e72`
- Source run id: `43279017693`
- Source event: `workflow_dispatch`
- Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/43279017693`
- Source tree sha256: `5b246815901157ad1612b52d7fafcee766081af126b6b984eb0ff6acd3f7d61f`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-11-12T18:30:45.082000+00:00`

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
- Actual coverage: `99.68%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total executed test cases: `65927`
- Executed means observed non-skipped JUnit testcase records, not
  collection count or distinct logical tests. Error records can describe
  setup or collection failures rather than a test body run.
- Only measured positive durations enter the slowest-test ranking.
  Older CI timed-row totals are not directly comparable with this count.
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `29.397` | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_keeps_package_discovery_contract_narrow` | `junit-unit-scripts-tooling.other.xml` |
| 2 | `22.602` | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 3 | `15.182` | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 4 | `10.897` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 5 | `10.845` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 6 | `10.724` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 7 | `10.606` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 8 | `10.466` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 9 | `10.398` | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 10 | `9.817` | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.engineering.ci.test_pr_lane_results` | 1 | 29.397 | 29.397 |
| 2 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 22.602 | 22.602 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.072 | 10.606 |
| 4 | `tests.unit.iuphar_target_class.test_acceptance` | 3 | 20.926 | 7.043 |
| 5 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 15.182 | 15.182 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.897 | 10.897 |
| 7 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.845 | 10.845 |
| 8 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.724 | 10.724 |
| 9 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.398 | 10.398 |
| 10 | `tests.performance.test_measure_merger_input` | 1 | 9.817 | 9.817 |

## Refresh Procedure

1. Download original `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from the same qualified CI run. Verify its exact head, all 17 shards, module nonregression and both hard coverage gates; report the overall workflow separately.
2. If XML expired or measured inputs changed, obtain a new complete measurement. Use a fresh Nightly or a verified `--local-manifest`; logs and supplied percentages cannot replace the original XML.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --coverage-xml <original-xml> --source-commit <full-40-character-sha> --source-run-id <run-id> ...` with matching same-run duration inputs. The CLI rejects percentage overrides and input drift, and retains the XML measurement time instead of stamping the current time.
4. A legacy JSON timed-row count requires raw `--junit` inputs for the complete recorded source inventory; the updater rejects a partial or legacy-only refresh before writing outputs.
5. Commit the updated baseline and branch-consumable telemetry summary layer together.
