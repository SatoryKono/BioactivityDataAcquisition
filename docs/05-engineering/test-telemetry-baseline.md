______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-04'

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

- Source branch: `codex/architecture-coverage-closeout-11854-11899`
- Source commit: `0d89b40862340ad62cd361b8abbd080c64c15264`
- Source run id: `local-full-coverage-wave-32`
- Source event: `local_coverage_verify`
- Source run URL: `pending`
- Source tree sha256: `9bc4cbef5dc67035c795d600d665ff503ddf067cb59078cc7b873c28dae90db8`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-10-04T00:31:16.998248+00:00`

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
- Actual coverage: `99.74%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `32354`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `20.009` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | `17.057` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | `16.625` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | `12.306` | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 5 | `11.032` | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 6 | `10.774` | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 7 | `10.727` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 8 | `10.719` | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 9 | `10.462` | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 10 | `9.917` | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 43.599 | 17.057 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 21.856 | 10.462 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.446 | 10.727 |
| 4 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.009 | 20.009 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 12.306 | 12.306 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.032 | 11.032 |
| 7 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.774 | 10.774 |
| 8 | `tests.contract.test_provider_contract_drift_replay` | 1 | 8.608 | 8.608 |
| 9 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 8.058 | 8.058 |
| 10 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 1 | 8.029 | 8.029 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
