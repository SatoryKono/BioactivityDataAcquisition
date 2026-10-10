# Slowest Tests

Source commit: `1bfc36a0c6bf9cbd101e1e8e8bc82bbb03a33cba`
Source run id: `local-pr12131-final-1bfc36a-w2`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33495`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 26.518 | `tests.unit.scripts.engineering.qa.test_proof_or_stop::test_full_suite_wrapper_is_fail_closed[different_lane]` | `unit-scripts-tooling-other.xml` |
| 2 | 20.019 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 3 | 16.199 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 15.42 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 5 | 15.127 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 6 | 11.154 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 7 | 11.113 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | 10.74 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 9 | 10.738 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 10 | 10.511 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 11 | 9.387 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 12 | 9.369 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 13 | 8.485 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 14 | 8.032 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |
| 15 | 7.694 | `tests.integration.idempotency.test_reproducibility_idempotency_gate::test_consolidation_idempotency_contract_guard` | `integration.xml` |
| 16 | 7.458 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |
| 17 | 7.144 | `tests.integration.config.test_pubchem_property_vocabulary_inventory::test_pubchem_property_urn_inventory_covers_observed_fixture_values` | `integration.xml` |
| 18 | 7.116 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 19 | 6.384 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 20 | 6.101 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 21 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 22 | 5.951 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 23 | 5.785 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `unit-other.xml` |
| 24 | 5.73 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 25 | 5.726 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 34.955 | 16.199 |
| 2 | `tests.unit.scripts.engineering.qa.test_proof_or_stop` | 1 | 26.518 | 26.518 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.478 | 10.74 |
| 4 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.019 | 20.019 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 16.237 | 10.511 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 2 | 15.943 | 8.485 |
| 7 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 15.42 | 15.42 |
| 8 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 15.127 | 15.127 |
| 9 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.154 | 11.154 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.113 | 11.113 |

