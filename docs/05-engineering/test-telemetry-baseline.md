______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-09'

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

- Source branch: `codex/pr12096-closeout-20261007`
- Source commit: `dc61bfdfc64606fad502dfb369dc6c15eff995d5`
- Source run id: `local-local-verify-pr12096-20261009-final6`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `2e6272e00d997c0a257e7dc45568a848e5a8cd169ef89a65d8bfccc4108a8f26`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-09T00:28:43.160492+00:00`

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
- Actual coverage: `99.67%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `33458`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `230.123` | `tests.unit.application.services.run_reports.test_composite_report::test_damaged_child_report_cannot_produce_success_message[wrong_identity]` | `unit-application.xml` |
| 2 | `35.382` | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 3 | `32.024` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | `27.687` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-publication]` | `integration.xml` |
| 5 | `26.643` | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[yaml]` | `smoke.xml` |
| 6 | `25.484` | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 7 | `22.62` | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 8 | `20.018` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 9 | `19.778` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-molecule]` | `integration.xml` |
| 10 | `18.808` | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.application.services.run_reports.test_composite_report` | 1 | 230.123 | 230.123 |
| 2 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 9 | 150.386 | 27.687 |
| 3 | `tests.unit.infrastructure.export.test_export_adapters` | 1 | 35.382 | 35.382 |
| 4 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 1 | 32.024 | 32.024 |
| 5 | `tests.smoke.test_smoke.TestRuntimeDependencies` | 1 | 26.643 | 26.643 |
| 6 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders` | 1 | 25.484 | 25.484 |
| 7 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 22.62 | 22.62 |
| 8 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.468 | 10.745 |
| 9 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.018 | 20.018 |
| 10 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 16.18 | 16.18 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
