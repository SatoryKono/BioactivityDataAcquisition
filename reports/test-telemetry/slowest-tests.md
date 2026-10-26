# Slowest Tests

Source commit: `aff36be4c4c080f4ca92a189189d7c5dab208618`
Source run id: `0`
Source event: `push`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34037`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 49.219 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 25.175 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 20.887 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli::test_direct_module_entrypoint_json_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 4 | 18.333 | `tests.unit.repo_backed.scripts.diagrams.test_generate_pipeline_dataflows::test_ir_resolves_effective_chembl_activity_policy` | `repo-backed-unit-tooling.xml` |
| 5 | 17.346 | `tests.unit.scripts.ops.observability.test_green_optional_inputs::test_optional_eligibility_matches_normalized_runtime_filter[values0-doi IS NOT NULL-True]` | `unit-scripts-tooling-other.xml` |
| 6 | 12.116 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 7 | 11.447 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 8 | 11.374 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 9 | 11.37 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | 11.176 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 11 | 11.018 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 12 | 10.906 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 13 | 10.838 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 14 | 10.83 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 15 | 9.824 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_status_failure_is_classified_but_supported_recovery_succeeds` | `repo-backed-unit-ops.xml` |
| 16 | 9.679 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `repo-backed-unit-ops.xml` |
| 17 | 9.465 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 18 | 8.78 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 19 | 8.772 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 20 | 8.608 | `tests.unit.scripts.repo.test_check_no_partial_tree::test_guard_flags_partial_tree_commit_in_range` | `unit-scripts-tooling-other.xml` |
| 21 | 8.357 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 22 | 8.341 | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager::test_direct_script_help_bootstraps_repository_imports` | `repo-backed-unit-ops.xml` |
| 23 | 8.217 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 24 | 7.875 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 25 | 7.619 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_report_recursively_redacts_observations_and_classifications` | `repo-backed-unit-ops.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 49.219 | 49.219 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 5 | 48.703 | 12.116 |
| 3 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 47.64 | 25.175 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.736 | 10.906 |
| 5 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli` | 1 | 20.887 | 20.887 |
| 6 | `tests.unit.repo_backed.scripts.diagrams.test_generate_pipeline_dataflows` | 1 | 18.333 | 18.333 |
| 7 | `tests.unit.scripts.ops.observability.test_green_optional_inputs` | 1 | 17.346 | 17.346 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.374 | 11.374 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.37 | 11.37 |
| 10 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 11.176 | 11.176 |

