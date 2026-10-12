# Slowest Tests

Source commit: `4eefc2be8d32cc968e4fc5d2696a02dbce703978`
Source run id: `local-bioetl-local-coverage-pr12138`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33513`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 44.119 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 31.48 | `tests.smoke.test_smoke.TestDevDependencies::test_dev_dependency_importable[hypothesis]` | `smoke.xml` |
| 3 | 24.102 | `tests.unit.scripts.ci.test_test_telemetry_provenance::test_accepts_equal_inputs_and_confirmed_squash_tree` | `unit-scripts-tooling-other.xml` |
| 4 | 21.944 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | 20.018 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 6 | 17.706 | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[structlog]` | `smoke.xml` |
| 7 | 14.764 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | 13.812 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 9 | 13.059 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 10 | 12.127 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 11 | 11.197 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 12 | 11.07 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 13 | 10.891 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 14 | 10.155 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 15 | 9.898 | `tests.smoke.test_smoke.TestDevDependencies::test_dev_only_dependency_importable[importlinter]` | `smoke.xml` |
| 16 | 9.357 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 17 | 9.139 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 18 | 8.28 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `repo-backed-unit-ops.xml` |
| 19 | 8.026 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |
| 20 | 7.999 | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[prometheus_client]` | `smoke.xml` |
| 21 | 7.986 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 22 | 7.301 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 23 | 7.165 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 24 | 7.027 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 25 | 6.9 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_report_recursively_redacts_observations_and_classifications` | `repo-backed-unit-ops.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 44.119 | 44.119 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.456 | 21.944 |
| 3 | `tests.smoke.test_smoke.TestDevDependencies` | 2 | 41.378 | 31.48 |
| 4 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 4 | 36.446 | 12.127 |
| 5 | `tests.smoke.test_smoke.TestRuntimeDependencies` | 2 | 25.705 | 17.706 |
| 6 | `tests.unit.scripts.ci.test_test_telemetry_provenance` | 1 | 24.102 | 24.102 |
| 7 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.267 | 11.197 |
| 8 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.018 | 20.018 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 14.764 | 14.764 |
| 10 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 13.812 | 13.812 |

