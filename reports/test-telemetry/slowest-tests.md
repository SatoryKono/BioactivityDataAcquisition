# Slowest Tests

Source commit: `8eb80155ad7cf00b1dbe9a849310602352504ff9`
Source run id: `43360903744`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/43360903744`
Refresh status: `captured`
Executed test cases: `66278`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 21.064 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 17.3 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 11.685 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 4 | 10.877 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 5 | 10.844 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 6 | 10.82 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 7 | 10.586 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 8 | 10.465 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 9 | 10.448 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 10 | 10.386 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 11 | 9.993 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 12 | 8.539 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 13 | 8.478 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `junit.integration.xml` |
| 14 | 8.181 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 15 | 7.806 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 16 | 7.459 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 17 | 7.073 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 18 | 6.629 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 6.499 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 20 | 6.208 | `tests.unit.scripts.engineering.ci.test_pytest_abort_diagnostic_adapter::test_no_fallback_skips_second_pass_after_timeout` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 5.806 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 5.546 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `junit.integration.xml` |
| 24 | 5.393 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `junit.integration.xml` |
| 25 | 5.256 | `tests.integration.test_runtime_metric_emission_consistency::test_direct_runtime_metric_emitters_match_declared_label_contracts` | `junit.integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 22.529 | 11.685 |
| 2 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 21.064 | 21.064 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.034 | 10.586 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 17.3 | 17.3 |
| 5 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 13.265 | 7.459 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.877 | 10.877 |
| 7 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.82 | 10.82 |
| 8 | `tests.integration.test_runtime_metric_emission_consistency` | 2 | 10.802 | 5.546 |
| 9 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 10.465 | 10.465 |
| 10 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.386 | 10.386 |
