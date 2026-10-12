______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-12'

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

- Source branch: `fix/debt-baseline-markdown`
- Source commit: `4eefc2be8d32cc968e4fc5d2696a02dbce703978`
- Source run id: `local-bioetl-local-coverage-pr12138`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `d6190f99b57054754f6f881231a8b80d2ac08a5a659121c398e9c42920cd44f7`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-12T17:02:01.736218+00:00`

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

- Total collected test cases: `33513`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `44.119` | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | `31.48` | `tests.smoke.test_smoke.TestDevDependencies::test_dev_dependency_importable[hypothesis]` | `smoke.xml` |
| 3 | `24.102` | `tests.unit.scripts.ci.test_test_telemetry_provenance::test_accepts_equal_inputs_and_confirmed_squash_tree` | `unit-scripts-tooling-other.xml` |
| 4 | `21.944` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | `20.018` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 6 | `17.706` | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[structlog]` | `smoke.xml` |
| 7 | `14.764` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | `13.812` | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 9 | `13.059` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 10 | `12.127` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 44.119 | 44.119 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.456 | 21.944 |
| 3 | `tests.smoke.test_smoke.TestDevDependencies` | 2 | 41.378 | 31.48 |
| 4 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 4 | 36.446 | 12.127 |
| 5 | `tests.smoke.test_smoke.TestRuntimeDependencies` | 2 | 25.705 | 17.706 |
| 6 | `tests.unit.scripts.ci.test_test_telemetry_provenance` | 1 | 24.102 | 24.102 |
| 7 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.267 | 11.197 |
| 8 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.018 | 20.018 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 14.764 | 14.764 |
| 10 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 13.812 | 13.812 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
