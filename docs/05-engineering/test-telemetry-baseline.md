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

- Source branch: `fix/12009-ruleset-contract-alignment`
- Source commit: `1a5485030ae20b0f767ef4045f7287a2f090f2fc`
- Source run id: `local-bioetl-local-coverage-pr12234-1a5485030ae20b0f767ef4045f7287a2f090f2fc`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `e70c02b3f855c4ca476ea85789a7e617e08c139d4353e0d69460fce434f5b818`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-17T13:11:30.245860+00:00`

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
| 1 | `141.106` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | `25.693` | `tests.unit.scripts.ci.test_update_test_telemetry_baseline::test_legacy_only_refresh_rejects_before_overwriting_baseline` | `unit-scripts-tooling-other.xml` |
| 3 | `25.321` | `tests.unit.helpers.test_vcr_config_fixture_routing::test_every_in_tree_vcr_config_fixture_routes_through_base_helper` | `unit-other.xml` |
| 4 | `23.871` | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 5 | `23.619` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | `22.879` | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 7 | `22.236` | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 8 | `18.159` | `tests.unit.repo_backed.scripts.ai.test_npm_runtime_contract::test_node_and_lock_parity[None]` | `repo-backed-unit-tooling.xml` |
| 9 | `15.58` | `tests.contract.test_composite_merge_golden::test_composite_merge_golden_seed_priority_is_stable` | `contract-confidence.xml` |
| 10 | `15.12` | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[structlog]` | `smoke.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 141.106 | 141.106 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 48.623 | 23.619 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 30.134 | 10.611 |
| 4 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline` | 1 | 25.693 | 25.693 |
| 5 | `tests.unit.helpers.test_vcr_config_fixture_routing` | 1 | 25.321 | 25.321 |
| 6 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 23.871 | 23.871 |
| 7 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 22.879 | 22.879 |
| 8 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 1 | 22.236 | 22.236 |
| 9 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.209 | 11.218 |
| 10 | `tests.unit.repo_backed.scripts.ai.test_npm_runtime_contract` | 1 | 18.159 | 18.159 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. A legacy JSON timed-row count requires raw `--junit` inputs for the complete recorded source inventory; the updater rejects a partial or legacy-only refresh before writing outputs.
5. Commit the updated baseline and branch-consumable telemetry summary layer together.
