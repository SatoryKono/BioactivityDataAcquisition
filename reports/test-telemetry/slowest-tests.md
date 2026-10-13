# Slowest Tests

Source commit: `179eacffd4dd9bd57add25a2ed90071b096d2588`
Source run id: `local-bioetl-local-coverage-pr11990-final3`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33571`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 143.035 | `tests.unit.interfaces.cli.test_workflow_cli::test_multi_pipeline_push_failure_preserves_success_and_report` | `unit-other.xml` |
| 2 | 20.012 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 3 | 19.283 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 14.793 | `tests.unit.interfaces.cli.commands.test_health.TestHealthServerCommand::test_start_health_observability_starts_metrics_server_when_enabled` | `unit-other.xml` |
| 5 | 14.338 | `tests.security.test_security.TestVCRCassetteSanitization::test_no_authorization_headers_with_real_values[Authorization]` | `security.xml` |
| 6 | 12.581 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 7 | 12.176 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 8 | 11.611 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 11.516 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | 11.456 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 11.434 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 12 | 11.242 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 13 | 11.008 | `tests.unit.application.test_main_module::test_main_block_executed_via_subprocess` | `unit-application.xml` |
| 14 | 10.942 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 15 | 10.877 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 16 | 10.486 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 17 | 9.95 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `repo-backed-unit-ops.xml` |
| 18 | 9.523 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_report_recursively_redacts_observations_and_classifications` | `repo-backed-unit-ops.xml` |
| 19 | 9.131 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_successful_recovery_has_per_command_deadlines_and_all_categories` | `repo-backed-unit-ops.xml` |
| 20 | 8.636 | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager::test_direct_script_help_bootstraps_repository_imports` | `repo-backed-unit-ops.xml` |
| 21 | 8.021 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_status_failure_is_classified_but_supported_recovery_succeeds` | `repo-backed-unit-ops.xml` |
| 22 | 7.991 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 23 | 7.687 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 24 | 7.681 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 25 | 7.565 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.interfaces.cli.test_workflow_cli` | 1 | 143.035 | 143.035 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 6 | 60.083 | 12.581 |
| 3 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 43.07 | 19.283 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.376 | 11.434 |
| 5 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.012 | 20.012 |
| 6 | `tests.unit.interfaces.cli.commands.test_health.TestHealthServerCommand` | 1 | 14.793 | 14.793 |
| 7 | `tests.security.test_security.TestVCRCassetteSanitization` | 1 | 14.338 | 14.338 |
| 8 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.516 | 11.516 |
| 9 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.456 | 11.456 |
| 10 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 11.242 | 11.242 |

