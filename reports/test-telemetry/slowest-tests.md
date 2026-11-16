# Slowest Tests

Source commit: `f212b662cc9da1f4536e151106a4400c460d70c8`
Source run id: `local-host-hooks-final-capture-20261116-07`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `39183`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 32.492 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline::test_legacy_only_refresh_rejects_before_overwriting_baseline` | `unit-scripts-tooling-other.xml` |
| 2 | 28.133 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 26.112 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `repo-backed-unit-tooling.xml` |
| 4 | 25.934 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `unit-scripts-tooling-other.xml` |
| 5 | 21.512 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory::test_canonical_inventory_public_entrypoint_reports_repo_signal_contract` | `repo-backed-unit-tooling.xml` |
| 6 | 17.598 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 7 | 17.294 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 8 | 17.242 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 9 | 17.006 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 10 | 16.41 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[True-None]` | `unit-scripts-tooling-other.xml` |
| 11 | 16.307 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `unit-other.xml` |
| 12 | 16.042 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[False-None]` | `unit-scripts-tooling-other.xml` |
| 13 | 14.28 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 14 | 14.029 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `security.xml` |
| 15 | 13.88 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 16 | 12.872 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `unit-scripts-tooling-other.xml` |
| 17 | 12.429 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `unit-scripts-tooling-other.xml` |
| 18 | 11.937 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 19 | 11.695 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 20 | 11.646 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 21 | 11.481 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 22 | 11.427 | `tests.unit.iuphar_target_class.test_acceptance::test_filtered_child_cannot_publish_unexecuted_passes[]` | `unit-other.xml` |
| 23 | 11.232 | `tests.unit.iuphar_target_class.test_acceptance::test_deselected_child_is_not_reported_as_pass[]` | `unit-other.xml` |
| 24 | 11.203 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 25 | 10.992 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 62.737 | 28.133 |
| 2 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline` | 1 | 32.492 | 32.492 |
| 3 | `tests.unit.scripts.test_hook_installation` | 2 | 32.452 | 16.41 |
| 4 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 26.112 | 26.112 |
| 5 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 25.934 | 25.934 |
| 6 | `tests.unit.iuphar_target_class.test_acceptance` | 2 | 22.659 | 11.427 |
| 7 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.195 | 11.203 |
| 8 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory` | 1 | 21.512 | 21.512 |
| 9 | `tests.integration.test_runtime_metric_emission_consistency` | 1 | 17.294 | 17.294 |
| 10 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 17.242 | 17.242 |
