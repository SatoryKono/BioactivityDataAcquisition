# Slowest Tests

Source commit: `3d33cc6515c9446bd1388afca3564f50e8b3b816`
Source run id: `44760615105`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/44760615105`
Refresh status: `captured`
Executed test cases: `69958`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 24.408 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 18.799 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 15.759 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `junit-unit-scripts-tooling.other.xml` |
| 4 | 12.46 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 5 | 12.445 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 6 | 11.376 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 7 | 11.37 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 8 | 10.921 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 9 | 10.879 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 10 | 10.639 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 11 | 10.637 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 12 | 10.503 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 13 | 10.409 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 14 | 10.009 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 15 | 9.974 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 16 | 8.876 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `junit.integration.xml` |
| 17 | 8.271 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 18 | 7.903 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit-fast.unit-other.xml` |
| 19 | 6.902 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 6.598 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 6.485 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 22 | 6.457 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit-fast.unit-other.xml` |
| 23 | 6.291 | `tests.security.test_security.TestPathTraversal::test_no_unsanitized_path_joins` | `junit.security.xml` |
| 24 | 6.185 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `junit.integration.xml` |
| 25 | 6.142 | `tests.integration.test_runtime_metric_emission_consistency::test_direct_runtime_metric_emitters_match_declared_label_contracts` | `junit.integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 24.408 | 24.408 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.14 | 10.637 |
| 3 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 19.043 | 12.445 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 18.799 | 18.799 |
| 5 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 15.759 | 15.759 |
| 6 | `tests.unit.iuphar_target_class.test_normalization` | 2 | 14.388 | 7.903 |
| 7 | `tests.performance.test_measure_merger_input` | 1 | 12.46 | 12.46 |
| 8 | `tests.integration.test_runtime_metric_emission_consistency` | 2 | 12.327 | 6.185 |
| 9 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 11.376 | 11.376 |
| 10 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 11.37 | 11.37 |
