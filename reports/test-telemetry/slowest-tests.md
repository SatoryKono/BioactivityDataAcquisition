# Slowest Tests

Source commit: `600f461177194413ef23e37cf59834437ac5f583`
Source run id: `45080790597`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/45080790597`
Refresh status: `captured`
Executed test cases: `69968`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 24.707 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 18.632 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 15.644 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `junit-unit-scripts-tooling.other.xml` |
| 4 | 12.904 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 5 | 12.028 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 6 | 10.717 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 7 | 10.711 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 8 | 10.456 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 9 | 10.432 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 10 | 10.299 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 11 | 10.248 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 12 | 10.208 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 13 | 10.112 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 14 | 8.282 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 15 | 7.985 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit-fast.unit-other.xml` |
| 16 | 7.624 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 17 | 7.438 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 18 | 6.702 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit-fast.unit-other.xml` |
| 19 | 6.58 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 6.387 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit.unit-other.xml` |
| 21 | 6.382 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 22 | 6.284 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 6.146 | `tests.unit.iuphar_target_class.test_acceptance::test_deselected_child_is_not_reported_as_pass[]` | `junit.unit-other.xml` |
| 24 | 6.024 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[True-None]` | `junit-unit-scripts-tooling.other.xml` |
| 25 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 24.707 | 24.707 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 20.547 | 10.299 |
| 3 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 19.188 | 12.904 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 18.632 | 18.632 |
| 5 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 15.644 | 15.644 |
| 6 | `tests.unit.iuphar_target_class.test_normalization` | 2 | 15.609 | 7.985 |
| 7 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 2 | 13.089 | 6.702 |
| 8 | `tests.performance.test_measure_merger_input` | 1 | 12.028 | 12.028 |
| 9 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 10.717 | 10.717 |
| 10 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.711 | 10.711 |
