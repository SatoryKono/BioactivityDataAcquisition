# Slowest Tests

Source commit: `005a7dc6f77b792f6857b5880ca1af4cdbdd2adc`
Source run id: `local-coverage`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33138`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 20.025 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | 17.777 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 10.951 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 4 | 10.923 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 5 | 10.59 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 6 | 10.561 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 7 | 10.546 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 8 | 10.52 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 10.499 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 10 | 9.718 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 11 | 8.492 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 12 | 8.139 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 13 | 7.853 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 14 | 7.742 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 15 | 7.281 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 16 | 6.291 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 17 | 6.142 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration::test_bootstrapped_service_can_list_pipelines` | `unit-other.xml` |
| 18 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 19 | 5.947 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 20 | 5.245 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `unit-scripts-tooling-other.xml` |
| 21 | 5.122 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 22 | 5.116 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 23 | 5.026 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |
| 24 | 4.688 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[target]` | `integration.xml` |
| 25 | 4.435 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `contract-confidence.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 38.843 | 17.777 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.151 | 10.59 |
| 3 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.025 | 20.025 |
| 4 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 2 | 14.406 | 9.718 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.951 | 10.951 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.923 | 10.923 |
| 7 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.499 | 10.499 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 8.492 | 8.492 |
| 9 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 8.139 | 8.139 |
| 10 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.853 | 7.853 |

