# Slowest Tests

Source commit: `cfb336e41b1277242fc9749cdf5bb59011ad11f9`
Source run id: `44465749809`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/44465749809`
Refresh status: `captured`
Executed test cases: `69738`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 25.603 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 18.755 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 15.586 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `junit-unit-scripts-tooling.other.xml` |
| 4 | 12.412 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 5 | 12.374 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 6 | 10.98 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 7 | 10.806 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 8 | 10.774 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 9 | 10.732 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 10 | 10.647 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 11 | 10.518 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 12 | 10.513 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 13 | 10.405 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 14 | 10.36 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 15 | 7.39 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `junit.integration.xml` |
| 16 | 7.329 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit-fast.unit-other.xml` |
| 17 | 6.929 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 18 | 6.803 | `tests.unit.repo_backed.scripts.ai.mcp.test_agent_audit_regressions::test_github_powershell_child_env_is_isolated` | `junit-repo-backed-unit.tooling.xml` |
| 19 | 6.636 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 6.599 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 21 | 6.563 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 22 | 6.558 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 24 | 5.772 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit-fast.unit-other.xml` |
| 25 | 5.771 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 25.603 | 25.603 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 20.923 | 10.518 |
| 3 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 18.97 | 12.412 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 18.755 | 18.755 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 17.579 | 10.98 |
| 6 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 15.586 | 15.586 |
| 7 | `tests.unit.iuphar_target_class.test_normalization` | 2 | 13.892 | 7.329 |
| 8 | `tests.performance.test_measure_merger_input` | 1 | 12.374 | 12.374 |
| 9 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 10.806 | 10.806 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.774 | 10.774 |
