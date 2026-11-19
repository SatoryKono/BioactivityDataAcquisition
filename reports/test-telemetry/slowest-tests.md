# Slowest Tests

Source commit: `e4ed6d3ed379de7d40ecdba81fc7fba56fe7676a`
Source run id: `44459422990`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/44459422990`
Refresh status: `captured`
Executed test cases: `69341`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 17.025 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 14.629 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 12.972 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 4 | 12.323 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 5 | 10.83 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 6 | 10.599 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 7 | 10.572 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 8 | 10.398 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 9 | 10.318 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 10 | 10.276 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 11 | 10.034 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 12 | 9.429 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 13 | 8.913 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit-fast.unit-other.xml` |
| 14 | 8.746 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 15 | 7.643 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 16 | 7.191 | `tests.unit.iuphar_target_class.test_acceptance::test_deselected_child_is_not_reported_as_pass[]` | `junit.unit-other.xml` |
| 17 | 7.022 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit-fast.unit-other.xml` |
| 18 | 6.606 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 6.595 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit.unit-other.xml` |
| 20 | 6.569 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 21 | 6.495 | `tests.unit.iuphar_target_class.test_acceptance::test_filtered_child_cannot_publish_unexecuted_passes[]` | `junit.unit-other.xml` |
| 22 | 6.495 | `tests.unit.iuphar_target_class.test_acceptance::test_acceptance_report_marks_only_executed_checks` | `junit.unit-other.xml` |
| 23 | 6.186 | `tests.unit.iuphar_target_class.test_acceptance::test_acceptance_report_marks_only_executed_checks` | `junit-fast.unit-other.xml` |
| 24 | 6.149 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 25 | 6.078 | `tests.security.test_security.TestPathTraversal::test_no_unsanitized_path_joins` | `junit.security.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.iuphar_target_class.test_acceptance` | 4 | 26.367 | 7.191 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 20.716 | 10.398 |
| 3 | `tests.unit.iuphar_target_class.test_normalization` | 2 | 17.659 | 8.913 |
| 4 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 17.025 | 17.025 |
| 5 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 14.629 | 14.629 |
| 6 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 2 | 13.617 | 7.022 |
| 7 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 12.972 | 12.972 |
| 8 | `tests.performance.test_measure_merger_input` | 1 | 12.323 | 12.323 |
| 9 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.83 | 10.83 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.599 | 10.599 |
