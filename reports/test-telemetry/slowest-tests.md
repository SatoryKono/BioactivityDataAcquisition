# Slowest Tests

Source commit: `792a2ca96cc50e20a5d039f8baa7b01b3db5de58`
Source run id: `45117454919`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/45117454919`
Refresh status: `captured`
Executed test cases: `69968`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 25.182 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 18.242 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 15.368 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `junit-unit-scripts-tooling.other.xml` |
| 4 | 12.522 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 5 | 11.97 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 6 | 10.76 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 7 | 10.758 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 8 | 10.72 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 9 | 10.526 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 10 | 10.503 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 11 | 10.397 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 12 | 10.34 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 13 | 9.792 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 14 | 7.474 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 15 | 7.247 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `junit.integration.xml` |
| 16 | 6.799 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 17 | 6.707 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 18 | 6.538 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 6.197 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 20 | 6.139 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 5.935 | `tests.unit.iuphar_target_class.test_acceptance::test_deselected_child_is_not_reported_as_pass[]` | `junit.unit-other.xml` |
| 23 | 5.903 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[False-None]` | `junit-unit-scripts-tooling.other.xml` |
| 24 | 5.903 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[True-None]` | `junit-unit-scripts-tooling.other.xml` |
| 25 | 5.859 | `tests.unit.scripts.engineering.ci.test_pytest_abort_diagnostic_adapter::test_no_fallback_skips_second_pass_after_timeout` | `junit-unit-scripts-tooling.other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 25.182 | 25.182 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 20.9 | 10.503 |
| 3 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 18.242 | 18.242 |
| 4 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 18.109 | 11.97 |
| 5 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 15.368 | 15.368 |
| 6 | `tests.performance.test_measure_merger_input` | 1 | 12.522 | 12.522 |
| 7 | `tests.unit.scripts.test_hook_installation` | 2 | 11.806 | 5.903 |
| 8 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.76 | 10.76 |
| 9 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.758 | 10.758 |
| 10 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.72 | 10.72 |
