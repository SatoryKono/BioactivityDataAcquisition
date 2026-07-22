______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-22'

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

- Source branch: `codex/issues-6392-6401-clean`
- Source commit: `460eb53be1`
- Source run id: `local-pre-ci-issues-6392-6401-20260722`
- Refresh status: `captured`
- Refreshed at (UTC): `2026-07-22T17:03:50.836383+00:00`

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `95.61%`
- Threshold satisfied: `True`

## Duration Telemetry

- Total collected test cases: `11721`
- Freshness guard: `<=45 days` via `refreshed_at_utc`

### Top Slowest Tests

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | `12.016` | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_processed_records_distinguishes_empty_and_backend_unavailable` | `unit-parallel-safe.xml` |
| 2 | `5.874` | `tests.architecture.test_config_discrepancy_report_drift::test_config_discrepancy_report_matches_deterministic_generator` | `architecture-current-change.xml` |
| 3 | `4.581` | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_gate_rejects_cross_occurrence_source_artifacts` | `unit-parallel-safe.xml` |
| 4 | `4.264` | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_gate_rejects_render_source_without_valid_panel_scope[empty_panel_states]` | `unit-parallel-safe.xml` |
| 5 | `3.826` | `tests.contract.test_gold_entity_coverage_complete::test_each_gold_entity_is_strict_with_published_contract[chembl_activity]` | `serial-maintained.xml` |
| 6 | `3.618` | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `serial-maintained.xml` |
| 7 | `3.4` | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_gate_rejects_render_source_without_valid_panel_scope[missing]` | `unit-parallel-safe.xml` |
| 8 | `3.086` | `tests.unit.domain.schemas.openalex.test_publication_schema.TestOpenAlexPublicationSchema::test_year_range_validation` | `unit-parallel-safe.xml` |
| 9 | `2.451` | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `serial-maintained.xml` |
| 10 | `2.381` | `tests.unit.scripts.test_report_observability_metric_inventory::test_collect_metric_inventory_records_static_prometheus_collector_emitters` | `unit-parallel-safe.xml` |

### Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle` | 5 | 16.636 | 4.581 |
| 2 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 12.016 | 12.016 |
| 3 | `tests.contract.test_normalization_cross_layer_contracts` | 4 | 8.136 | 2.303 |
| 4 | `tests.architecture.test_config_discrepancy_report_drift` | 1 | 5.874 | 5.874 |
| 5 | `tests.unit.domain.schemas.openalex.test_publication_schema.TestOpenAlexPublicationSchema` | 2 | 4.876 | 3.086 |
| 6 | `tests.unit.scripts.test_report_observability_metric_inventory` | 2 | 4.697 | 2.381 |
| 7 | `tests.unit.scripts.qa.test_run_observability_closure_campaign` | 2 | 4.02 | 2.082 |
| 8 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 2 | 3.839 | 2.023 |
| 9 | `tests.contract.test_gold_entity_coverage_complete` | 1 | 3.826 | 3.826 |
| 10 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 3.618 | 3.618 |

## Refresh Procedure

1. Preferred path: download `reports/coverage/coverage.xml` and `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Fallback path: use resilient CI diagnostics artifacts (`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line from `parallel.log`) when the direct coverage artifact expired.
3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id> ...` with either direct artifacts or fallback diagnostics inputs.
4. Commit the updated baseline and branch-consumable telemetry summary layer together.
