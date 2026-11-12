# Slowest Tests

Source commit: `a50288c9f3b85623d34eabf0bfc396c971936567`
Source run id: `43295184976`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/43295184976`
Refresh status: `captured`
Executed test cases: `66005`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 16.784 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 2 | 11.482 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 3 | 11.01 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 4 | 10.881 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 5 | 10.831 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 6 | 10.589 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 7 | 10.467 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 8 | 10.393 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 9 | 9.813 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 10 | 9.795 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 11 | 9.356 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 12 | 8.694 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `junit.integration.xml` |
| 13 | 8.38 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 14 | 8.264 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 15 | 7.409 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 16 | 6.869 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit.unit-other.xml` |
| 17 | 6.754 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `junit.unit-other.xml` |
| 18 | 6.741 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 6.003 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 5.79 | `tests.unit.repo_backed.scripts.ai.mcp.test_agent_audit_regressions::test_github_powershell_child_env_is_isolated` | `junit-repo-backed-unit.tooling.xml` |
| 21 | 5.657 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `junit.integration.xml` |
| 22 | 5.651 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 23 | 5.438 | `tests.unit.scripts.engineering.ci.test_pytest_abort_diagnostic_adapter::test_no_fallback_skips_second_pass_after_timeout` | `junit-unit-scripts-tooling.other.xml` |
| 24 | 5.418 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `junit.integration.xml` |
| 25 | 5.391 | `tests.integration.infrastructure.durability.test_crash_silver::test_silver_mid_retry_gate_string_7` | `junit.integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.056 | 10.589 |
| 2 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 16.784 | 16.784 |
| 3 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 11.482 | 11.482 |
| 4 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 11.01 | 11.01 |
| 5 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.881 | 10.881 |
| 6 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.831 | 10.831 |
| 7 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.393 | 10.393 |
| 8 | `tests.unit.iuphar_target_class.test_normalization` | 1 | 9.813 | 9.813 |
| 9 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 9.795 | 9.795 |
| 10 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 9.356 | 9.356 |
