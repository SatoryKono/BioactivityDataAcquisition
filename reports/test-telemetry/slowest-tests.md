# Slowest Tests

Source commit: `1a5485030ae20b0f767ef4045f7287a2f090f2fc`
Source run id: `local-bioetl-local-coverage-pr12234-1a5485030ae20b0f767ef4045f7287a2f090f2fc`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34094`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 141.106 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 25.693 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline::test_legacy_only_refresh_rejects_before_overwriting_baseline` | `unit-scripts-tooling-other.xml` |
| 3 | 25.321 | `tests.unit.helpers.test_vcr_config_fixture_routing::test_every_in_tree_vcr_config_fixture_routes_through_base_helper` | `unit-other.xml` |
| 4 | 23.871 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 5 | 23.619 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 22.879 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 7 | 22.236 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 8 | 18.159 | `tests.unit.repo_backed.scripts.ai.test_npm_runtime_contract::test_node_and_lock_parity[None]` | `repo-backed-unit-tooling.xml` |
| 9 | 15.58 | `tests.contract.test_composite_merge_golden::test_composite_merge_golden_seed_priority_is_stable` | `contract-confidence.xml` |
| 10 | 15.12 | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[structlog]` | `smoke.xml` |
| 11 | 14.185 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 12 | 12.546 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 13 | 12.458 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 14 | 11.313 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 15 | 11.218 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 16 | 10.991 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 17 | 10.872 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 18 | 10.611 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 19 | 10.046 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 20 | 9.972 | `tests.unit.composition.runtime_builders.test_runner_builder_profiles::test_build_pipeline_runner_persists_manifest_before_empty_cached_bronze_fail` | `unit-other.xml` |
| 21 | 9.815 | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[true]` | `unit-scripts-tooling-other.xml` |
| 22 | 9.773 | `tests.smoke.test_smoke.TestDevDependencies::test_dev_dependency_importable[hypothesis]` | `smoke.xml` |
| 23 | 9.644 | `tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager::test_direct_script_help_bootstraps_repository_imports` | `repo-backed-unit-ops.xml` |
| 24 | 9.477 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `repo-backed-unit-ops.xml` |
| 25 | 8.827 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 141.106 | 141.106 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 48.623 | 23.619 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 30.134 | 10.611 |
| 4 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline` | 1 | 25.693 | 25.693 |
| 5 | `tests.unit.helpers.test_vcr_config_fixture_routing` | 1 | 25.321 | 25.321 |
| 6 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 23.871 | 23.871 |
| 7 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 22.879 | 22.879 |
| 8 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 1 | 22.236 | 22.236 |
| 9 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.209 | 11.218 |
| 10 | `tests.unit.repo_backed.scripts.ai.test_npm_runtime_contract` | 1 | 18.159 | 18.159 |

