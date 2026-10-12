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

- Source branch: `refactor/composite-checkpoint-persistence-params-1493320248371917823`
- Source commit: `6ba0e2803723369c2e4d48e4fdb320dcabaea63b`
- Source run id: `local-bioetl-local-coverage-uiltn594`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `3ec41186310457076a0292557c510cbb73d24e0b1fc6e3e68d263193d73dd823`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-12T15:25:39.623439+00:00`

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

- Total collected test cases: `33500`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `82.672` | `tests.unit.composition.test_workflow_cohort_lineage::test_real_gold_expiry_descendant_and_partial_resume_keep_scoped_history[None]` | `unit-other.xml` |
| 2 | `45.516` | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 3 | `24.477` | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 4 | `22.47` | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 5 | `20.221` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | `20.008` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 7 | `19.721` | `tests.unit.application.services.dq.test_checks_integrity_extended.TestCheckSCDIntegrityExtended::test_overlapping_validity_periods_warn` | `unit-application.xml` |
| 8 | `16.902` | `tests.unit.infrastructure.adapters.test_csv_filter_reader.TestCsvFilterReaderLoadFilterIds::test_load_filter_ids_returns_filter_load_result` | `unit-infrastructure.xml` |
| 9 | `15.17` | `tests.unit.application.test_main_module::test_main_block_executed_via_subprocess` | `unit-application.xml` |
| 10 | `14.488` | `tests.unit.application.test_issue_10518_application_compwf_a::test_chained_key_filter_applied_and_failed` | `unit-application.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.composition.test_workflow_cohort_lineage` | 1 | 82.672 | 82.672 |
| 2 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation` | 1 | 45.516 | 45.516 |
| 3 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 39.51 | 20.221 |
| 4 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 24.477 | 24.477 |
| 5 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 23.467 | 12.397 |
| 6 | `tests.unit.infrastructure.export.test_export_adapters` | 1 | 22.47 | 22.47 |
| 7 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.008 | 20.008 |
| 8 | `tests.unit.application.services.dq.test_checks_integrity_extended.TestCheckSCDIntegrityExtended` | 1 | 19.721 | 19.721 |
| 9 | `tests.unit.infrastructure.adapters.test_csv_filter_reader.TestCsvFilterReaderLoadFilterIds` | 1 | 16.902 | 16.902 |
| 10 | `tests.unit.application.test_main_module` | 1 | 15.17 | 15.17 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
