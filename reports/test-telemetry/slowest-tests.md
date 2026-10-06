# Slowest Tests

Source commit: `a63090e110ecf290d7a4d5dc8d84e75e7307ab1a`
Source run id: `local-coverage`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33138`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 20.024 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | 17.203 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 11.181 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 4 | 11.147 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 5 | 10.756 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 6 | 10.613 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 7 | 10.56 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 8 | 9.788 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 9.683 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 10 | 8.286 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 11 | 7.986 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 12 | 7.917 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 13 | 7.411 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 14 | 7.091 | `tests.unit.composition.test_registry_protocol.TestDataSourceCreatorHelper::test_provider_registry_has_list_keys` | `unit-other.xml` |
| 15 | 6.825 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 16 | 6.324 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 17 | 6.133 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 18 | 6.056 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 19 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 20 | 5.31 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 21 | 4.974 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |
| 22 | 4.941 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `unit-scripts-tooling-other.xml` |
| 23 | 4.657 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_build_field_matrix_rows_covers_entity_profile_and_generic_rules` | `repo-backed-unit-tooling.xml` |
| 24 | 4.605 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 25 | 4.604 | `tests.security.test_sql_injection_prevention.TestSQLInjectionPrevention::test_no_string_concatenation_in_sql_queries` | `security.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 36.674 | 17.203 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.369 | 10.756 |
| 3 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.024 | 20.024 |
| 4 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.181 | 11.181 |
| 5 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.147 | 11.147 |
| 6 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.56 | 10.56 |
| 7 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 8.286 | 8.286 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.986 | 7.986 |
| 9 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 7.917 | 7.917 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 7.411 | 7.411 |

