# Slowest Tests

Source commit: `0325fefc75c6159d9bc6d7865e2c0a9e71244e86`
Source run id: `local-coverage`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33596`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 20.026 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | 18.054 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 11.407 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 4 | 11.284 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 5 | 11.068 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 10.984 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 7 | 10.98 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | 10.601 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 9 | 10.558 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 10 | 10.513 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 11 | 10.503 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 12 | 9.211 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 13 | 7.733 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 14 | 7.335 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |
| 15 | 7.047 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 16 | 6.63 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 17 | 6.603 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 18 | 6.421 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `unit-scripts-tooling-other.xml` |
| 19 | 6.415 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_exposes_shared_chembl_policy_surfaces` | `contract-confidence.xml` |
| 20 | 6.385 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `unit-other.xml` |
| 21 | 6.364 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `unit-scripts-tooling-other.xml` |
| 22 | 6.272 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 23 | 6.236 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-target]` | `integration.xml` |
| 24 | 6.172 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `integration.xml` |
| 25 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 39.635 | 18.054 |
| 2 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 3 | 24.978 | 11.407 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.159 | 10.601 |
| 4 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.026 | 20.026 |
| 5 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 11.284 | 11.284 |
| 6 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.984 | 10.984 |
| 7 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 10.98 | 10.98 |
| 8 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.503 | 10.503 |
| 9 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 9.211 | 9.211 |
| 10 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 7.733 | 7.733 |

