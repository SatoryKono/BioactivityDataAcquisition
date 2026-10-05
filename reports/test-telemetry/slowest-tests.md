# Slowest Tests

Source commit: `84524a90deabcf2e4625b0bcf9349a7d59933d56`
Source run id: `local-coverage`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `32928`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 24.856 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 2 | 20.025 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 3 | 18.634 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 14.579 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 5 | 13.856 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 11.029 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 7 | 10.666 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 8 | 10.594 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 9 | 10.51 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 10 | 10.498 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 11 | 9.626 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 12 | 9.602 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 13 | 9.368 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 14 | 8.256 | `tests.unit.composition.test_registry_protocol.TestPipelineRegistryUnifiedAPI::test_list_keys_returns_list` | `unit-other.xml` |
| 15 | 7.863 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 16 | 7.619 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 17 | 7.313 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 18 | 7.083 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 19 | 6.832 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 20 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 21 | 5.551 | `tests.security.test_sql_injection_prevention.TestSQLInjectionPrevention::test_no_string_concatenation_in_sql_queries` | `security.xml` |
| 22 | 5.313 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `integration.xml` |
| 23 | 5.044 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generated_facts_validate_against_published_schemas` | `unit-scripts-tooling-passport.xml` |
| 24 | 4.953 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |
| 25 | 4.76 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 57.346 | 24.856 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.26 | 10.666 |
| 3 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.025 | 20.025 |
| 4 | `tests.unit.scripts.docs.passports.test_passport_projector` | 2 | 14.646 | 9.602 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 14.579 | 14.579 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.029 | 11.029 |
| 7 | `tests.contract.test_provider_contract_drift_replay` | 1 | 10.51 | 10.51 |
| 8 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.498 | 10.498 |
| 9 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 9.626 | 9.626 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 9.368 | 9.368 |

