# Slowest Tests

Source commit: `909f9c8f602c16cd67ee5b8b92fd7a83b3079b0d`
Source run id: `local-ci-5801-local-capture`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `32986`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 20.025 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | 19.053 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 13.291 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 4 | 12.565 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 5 | 11.165 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 10.902 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 7 | 10.792 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 8 | 10.542 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 9 | 10.527 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 10 | 10.456 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 11 | 8.994 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 12 | 8.349 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 13 | 8.096 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 14 | 7.587 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 15 | 7.224 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |
| 16 | 6.772 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 17 | 6.699 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 18 | 6.368 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `unit-other.xml` |
| 19 | 6.072 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 20 | 6.006 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 21 | 5.743 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `contract-confidence.xml` |
| 22 | 5.655 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `contract-confidence.xml` |
| 23 | 5.104 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `unit-scripts-tooling-other.xml` |
| 24 | 4.903 | `tests.security.test_sql_injection_prevention.TestSQLInjectionPrevention::test_no_string_concatenation_in_sql_queries` | `security.xml` |
| 25 | 4.892 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.01 | 19.053 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.069 | 10.542 |
| 3 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.025 | 20.025 |
| 4 | `tests.contract.test_provider_contract_drift_replay` | 1 | 13.291 | 13.291 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 12.565 | 12.565 |
| 6 | `tests.contract.test_normalization_cross_layer_contracts` | 2 | 11.398 | 5.743 |
| 7 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.902 | 10.902 |
| 8 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.456 | 10.456 |
| 9 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 8.994 | 8.994 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 8.349 | 8.349 |

