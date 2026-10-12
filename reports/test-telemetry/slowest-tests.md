# Slowest Tests

Source commit: `dfc1370923e4f685f89b06c0132d501765eea40f`
Source run id: `local-pr12187-review-sync-20261012`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33481`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 44.876 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 35.101 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 3 | 20.018 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 4 | 19.562 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 5 | 18.488 | `tests.unit.repo_backed.scripts.ops.test_migrate_gold_parquet_to_delta::test_apply_preserves_rows_normalizes_metadata_and_is_idempotent` | `repo-backed-unit-ops.xml` |
| 6 | 16.425 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 7 | 12.319 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_adr_analysis_wrapper_startup_contract[None]` | `repo-backed-unit-tooling.xml` |
| 8 | 12.171 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 9 | 11.151 | `tests.unit.repo_backed.scripts.test_check_skills_mirror::test_repository_skill_parity_contract_passes` | `repo-backed-unit-tooling.xml` |
| 10 | 11.14 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 11.005 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 12 | 10.856 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 13 | 10.729 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 14 | 10.453 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 15 | 10.452 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 16 | 9.702 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 17 | 9.55 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 18 | 8.033 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |
| 19 | 7.693 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 20 | 7.264 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `repo-backed-unit-ops.xml` |
| 21 | 7.24 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 22 | 7.196 | `tests.unit.scripts.engineering.qa.test_proof_or_stop::test_full_suite_wrapper_is_fail_closed[different_argv]` | `unit-scripts-tooling-other.xml` |
| 23 | 6.762 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 24 | 6.315 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 25 | 6.08 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 44.876 | 44.876 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 35.677 | 16.425 |
| 3 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders` | 1 | 35.101 | 35.101 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.861 | 11.005 |
| 5 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 2 | 20.352 | 12.319 |
| 6 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.018 | 20.018 |
| 7 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 19.562 | 19.562 |
| 8 | `tests.unit.repo_backed.scripts.ops.test_migrate_gold_parquet_to_delta` | 1 | 18.488 | 18.488 |
| 9 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 17.716 | 10.452 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 12.171 | 12.171 |

