# Slowest Tests

Source commit: `43546a3daf6203e9d36f9fdf30b299e8954a0ccf`
Source run id: `33159969914`
Refresh status: `captured`
Collected test cases: `49169`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 21.321 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | 12.364 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 3 | 11.015 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 4 | 10.962 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 5 | 9.315 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 6 | 7.505 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 7 | 7.427 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `junit.unit-other.xml` |
| 8 | 7.333 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.xml` |
| 9 | 6.335 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 10 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.xml` |
| 11 | 5.36 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.xml` |
| 12 | 4.968 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 13 | 4.967 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.xml` |
| 14 | 4.199 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `junit-contract-confidence.xml` |
| 15 | 4.155 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_token_warnings_stay_on_stderr[Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 -Purpose 'test MCP'-OPTIONAL_TOKEN is not set for test MCP]` | `junit-repo-backed-unit.xml` |
| 16 | 4.141 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_pipeline_normalization_field_matrix_1223__c8b0b2c2` | `junit-repo-backed-unit.xml` |
| 17 | 4.078 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `junit-contract-confidence.xml` |
| 18 | 4.077 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_exposes_shared_chembl_policy_surfaces` | `junit-contract-confidence.xml` |
| 19 | 4.039 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_field_matrix__is_deterministic__61401586` | `junit-repo-backed-unit.xml` |
| 20 | 3.999 | `tests.integration.interfaces.test_cli_run_incremental.TestCliRunIncremental::test_run_help_displays_options` | `junit.integration.xml` |
| 21 | 3.994 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.xml` |
| 22 | 3.985 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_check_artifacts_detects_drift__unit_scripts_test_generate_pipeline_normalization_field_matrix_1213` | `junit-repo-backed-unit.xml` |
| 23 | 3.931 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.xml` |
| 24 | 3.931 | `tests.integration.interfaces.test_cli_run_dry_run.TestCliRunDryRun::test_dry_run_option_available` | `junit.integration.xml` |
| 25 | 3.91 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit-unit-scripts-tooling.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 4 | 48.631 | 21.321 |
| 2 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.354 | 4.199 |
| 3 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 3 | 12.165 | 4.141 |
| 4 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.962 | 10.962 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.315 | 9.315 |
| 6 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.505 | 7.505 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity` | 1 | 7.427 | 7.427 |
| 8 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.333 | 7.333 |
| 9 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.335 | 6.335 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.004 | 6.004 |

