# Slowest Tests

Source commit: `fb548dc02f67bd5a5fe5e99c38599eace56f0698`
Source run id: `43274669233`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/43274669233`
Refresh status: `captured`
Executed test cases: `65925`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 33.67 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_keeps_package_discovery_contract_narrow` | `junit-unit-scripts-tooling.other.xml` |
| 2 | 19.4 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch::test_host_transport_behavior` | `junit-repo-backed-unit.tooling.xml` |
| 3 | 17.851 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `junit-unit-scripts-tooling.other.xml` |
| 4 | 11.044 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 5 | 10.458 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 6 | 10.454 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 7 | 10.447 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 8 | 10.308 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 9 | 10.237 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 10 | 10.215 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 11 | 8.99 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 12 | 8.535 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `junit-unit-scripts-tooling.other.xml` |
| 13 | 8.35 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 14 | 7.49 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 15 | 6.512 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `junit-unit-scripts-tooling.other.xml` |
| 16 | 6.488 | `tests.unit.iuphar_target_class.test_normalization::test_multi_field_error_order_is_stable_across_hash_seeds` | `junit.unit-other.xml` |
| 17 | 6.447 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 18 | 6.186 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 6.149 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 20 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 5.657 | `tests.unit.scripts.engineering.ci.test_pytest_abort_diagnostic_adapter::test_no_fallback_skips_second_pass_after_timeout` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 5.65 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 5.291 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 24 | 5.226 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[True-None]` | `junit-unit-scripts-tooling.other.xml` |
| 25 | 5.068 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[False-None]` | `junit-unit-scripts-tooling.other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.engineering.ci.test_pr_lane_results` | 2 | 40.182 | 33.67 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 20.545 | 10.308 |
| 3 | `tests.unit.repo_backed.scripts.ai.mcp.test_host_transport_dispatch` | 1 | 19.4 | 19.4 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 17.851 | 17.851 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 17.491 | 11.044 |
| 6 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 13.14 | 7.49 |
| 7 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.458 | 10.458 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 10.454 | 10.454 |
| 9 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.447 | 10.447 |
| 10 | `tests.unit.scripts.test_hook_installation` | 2 | 10.294 | 5.226 |
