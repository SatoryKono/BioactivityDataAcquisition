# Slowest Tests

Source commit: `7017e7277a30fcf56cffd92fb5bd13879bd260f8`
Source run id: `31404786271`
Refresh status: `captured`
Collected test cases: `46500`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 21.66 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | 11.314 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 3 | 10.934 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 4 | 9.469 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 5 | 7.344 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 6 | 7.093 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `junit.unit-other.xml` |
| 7 | 6.259 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 8 | 5.926 | `tests.integration.interfaces.test_cli_run_incremental.TestCliRunIncremental::test_run_help_displays_options` | `junit.integration.xml` |
| 9 | 5.318 | `tests.integration.interfaces.test_cli_run_incremental.TestCliRunTypes::test_run_type_incremental_is_default` | `junit.integration.xml` |
| 10 | 5.137 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.xml` |
| 11 | 4.97 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.xml` |
| 12 | 4.798 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 13 | 4.734 | `tests.integration.config.test_chembl_policy_surface_parity::test_chembl_governed_fields_have_explicit_profile_classification` | `junit.integration.xml` |
| 14 | 4.44 | `tests.integration.config.test_pubchem_enum_parity::test_pubchem_standardization_status_parity_across_enum_config_profile_fixture_and_matrix` | `junit.integration.xml` |
| 15 | 4.314 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.xml` |
| 16 | 4.234 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit-unit-scripts-tooling.xml` |
| 17 | 4.105 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_exposes_shared_chembl_policy_surfaces` | `junit-contract-confidence.xml` |
| 18 | 4.102 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.xml` |
| 19 | 4.096 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `junit-contract-confidence.xml` |
| 20 | 4.093 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit-unit-scripts-tooling.xml` |
| 21 | 4.064 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.xml` |
| 22 | 3.948 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `junit-contract-confidence.xml` |
| 23 | 3.862 | `tests.contract.test_chembl_case_and_ontology_consistency::test_chembl_ontology_identifier_families_are_profile_and_matrix_aligned[profile0-chembl_assay-bao_format-bao:0000190-BAO_0000190]` | `junit-contract-confidence.xml` |
| 24 | 3.8 | `tests.integration.config.test_chembl_contract_registry_coverage::test_chembl_registry_fixture_and_contract_surfaces_stay_in_dynamic_parity` | `junit.integration.xml` |
| 25 | 3.628 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `junit.integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 4 | 47.972 | 21.66 |
| 2 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 12.429 | 4.234 |
| 3 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.149 | 4.105 |
| 4 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.469 | 9.469 |
| 5 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.344 | 7.344 |
| 6 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity` | 1 | 7.093 | 7.093 |
| 7 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.259 | 6.259 |
| 8 | `tests.integration.interfaces.test_cli_run_incremental.TestCliRunIncremental` | 1 | 5.926 | 5.926 |
| 9 | `tests.integration.interfaces.test_cli_run_incremental.TestCliRunTypes` | 1 | 5.318 | 5.318 |
| 10 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 5.137 | 5.137 |

