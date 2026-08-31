# Slowest Tests

Source commit: `a13dc554f0b9a1f0e2c5df7eb06209177010ede0`
Source run id: `33423158461`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/33423158461`
Refresh status: `captured`
Collected test cases: `49516`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 14.534 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | 12.287 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.xml` |
| 3 | 10.909 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 4 | 8.384 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 5 | 8.35 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 6 | 7.67 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 7 | 7.658 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 8 | 7.623 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 9 | 7.384 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `junit.unit-other.xml` |
| 10 | 7.316 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.xml` |
| 11 | 7.311 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.xml` |
| 12 | 7.298 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.xml` |
| 13 | 6.433 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 14 | 6.003 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.xml` |
| 15 | 4.875 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.xml` |
| 16 | 4.418 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 17 | 4.101 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 18 | 4.075 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_check_artifacts_detects_drift__unit_scripts_test_generate_pipeline_normalization_field_matrix_1213` | `junit-repo-backed-unit.xml` |
| 19 | 4.074 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_field_matrix__is_deterministic__61401586` | `junit-repo-backed-unit.xml` |
| 20 | 4.06 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_pipeline_normalization_field_matrix_1223__c8b0b2c2` | `junit-repo-backed-unit.xml` |
| 21 | 4.014 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_build_field_matrix_rows_covers_entity_profile_and_generic_rules` | `junit-repo-backed-unit.xml` |
| 22 | 3.723 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `junit-repo-backed-unit.xml` |
| 23 | 3.591 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `junit-repo-backed-unit.xml` |
| 24 | 3.463 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `junit-contract-confidence.xml` |
| 25 | 3.449 | `tests.integration.config.test_chembl_contract_registry_coverage::test_chembl_registry_fixture_and_contract_surfaces_stay_in_dynamic_parity` | `junit.integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 3 | 30.554 | 14.534 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 26.914 | 12.287 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 18.223 | 10.909 |
| 4 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 4 | 16.223 | 4.075 |
| 5 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.091 | 7.658 |
| 6 | `tests.contract.test_provider_contract_drift_replay` | 1 | 8.384 | 8.384 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.623 | 7.623 |
| 8 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity` | 1 | 7.384 | 7.384 |
| 9 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.298 | 7.298 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.003 | 6.003 |

