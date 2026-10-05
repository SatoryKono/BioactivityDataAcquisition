# Slowest Tests

Source commit: `090d7a74c56e9de8db2f96d9a183a9058a55ccc8`
Source run id: `local-full-coverage-wave-46`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `32830`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 87.023 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 26.372 | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager::test_post_start_source_gate_failure_cannot_report_success` | `repo-backed-unit-ops.xml` |
| 3 | 20.009 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 4 | 19.218 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | 16.16 | `tests.contract.test_composite_merge_golden::test_composite_merge_golden_seed_priority_is_stable` | `contract-confidence.xml` |
| 6 | 15.882 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 7 | 15.365 | `tests.unit.repo_backed.scripts.diagrams.test_generate_pipeline_dataflows::test_ir_resolves_effective_chembl_activity_policy` | `repo-backed-unit-tooling.xml` |
| 8 | 14.298 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 9 | 13.963 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | 13.799 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 13.391 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 12 | 13.26 | `tests.unit.repo_backed.scripts.ops.test_migrate_gold_parquet_to_delta::test_apply_preserves_rows_normalizes_metadata_and_is_idempotent` | `repo-backed-unit-ops.xml` |
| 13 | 11.457 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 14 | 11.414 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory::test_direct_module_entrypoint_help_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 15 | 11.279 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 16 | 11.247 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 17 | 10.981 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 18 | 10.778 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 19 | 10.657 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 20 | 10.53 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 21 | 10.213 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli::test_direct_module_entrypoint_json_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 22 | 10.03 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 23 | 9.525 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 24 | 8.819 | `tests.unit.repo_backed.scripts.ops.docker.test_check_network_preconditions::test_contract_lists_shared_networks` | `repo-backed-unit-ops.xml` |
| 25 | 8.042 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 87.023 | 87.023 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 40.856 | 19.218 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager` | 1 | 26.372 | 26.372 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.736 | 11.457 |
| 5 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.009 | 20.009 |
| 6 | `tests.contract.test_composite_merge_golden` | 1 | 16.16 | 16.16 |
| 7 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 15.882 | 15.882 |
| 8 | `tests.unit.repo_backed.scripts.diagrams.test_generate_pipeline_dataflows` | 1 | 15.365 | 15.365 |
| 9 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 14.298 | 14.298 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 13.963 | 13.963 |

