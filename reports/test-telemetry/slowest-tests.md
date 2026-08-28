# Slowest Tests

Source commit: `e331747c4a632e0c616e0bfdb6bcbfafb4a8897d`
Source run id: `33168461811`
Refresh status: `captured`
Collected test cases: `49250`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 14.784 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | 13.094 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.xml` |
| 3 | 10.938 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 4 | 9.247 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 5 | 8.86 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 6 | 8.707 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 7 | 8.188 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 8 | 7.433 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.xml` |
| 9 | 7.357 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.xml` |
| 10 | 7.306 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_tolerates_unavailable_remote_main_baseline_builder` | `junit-unit-scripts-tooling.xml` |
| 11 | 6.911 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.xml` |
| 12 | 6.003 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.xml` |
| 13 | 5.845 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 14 | 5.085 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.xml` |
| 15 | 4.847 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 16 | 4.783 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 17 | 4.334 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_token_warnings_stay_on_stderr[Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 -Purpose 'test MCP'-OPTIONAL_TOKEN is not set for test MCP]` | `junit-repo-backed-unit.xml` |
| 18 | 4.234 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 19 | 4.221 | `tests.unit.composition.test_registry_protocol.TestPipelineRegistryUnifiedAPI::test_list_keys_returns_list` | `junit.unit-other.xml` |
| 20 | 4.062 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_exposes_shared_chembl_policy_surfaces` | `junit-contract-confidence.xml` |
| 21 | 4.056 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `junit-contract-confidence.xml` |
| 22 | 4.048 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `junit-contract-confidence.xml` |
| 23 | 3.934 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_check_artifacts_detects_drift__unit_scripts_test_generate_pipeline_normalization_field_matrix_1213` | `junit-repo-backed-unit.xml` |
| 24 | 3.838 | `tests.contract.test_chembl_case_and_ontology_consistency::test_chembl_ontology_identifier_families_are_profile_and_matrix_aligned[profile0-chembl_assay-bao_format-bao:0000190-BAO_0000190]` | `junit-contract-confidence.xml` |
| 25 | 3.792 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_field_matrix__is_deterministic__61401586` | `junit-repo-backed-unit.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 35.19 | 13.094 |
| 2 | `tests.unit.scripts.docs.passports.test_passport_projector` | 3 | 32.351 | 14.784 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.033 | 8.188 |
| 4 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.166 | 4.062 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.938 | 10.938 |
| 6 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.247 | 9.247 |
| 7 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 2 | 7.726 | 3.934 |
| 8 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 6.911 | 6.911 |
| 9 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.003 | 6.003 |
| 10 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 5.085 | 5.085 |

