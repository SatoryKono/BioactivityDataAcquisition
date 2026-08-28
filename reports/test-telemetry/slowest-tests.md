# Slowest Tests

Source commit: `09ab9ac286bacb7eee3324e950603539a5c62ee6`
Source run id: `github-33149935203-1`
Refresh status: `captured`
Collected test cases: `49226`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 21.002 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-unit-scripts-tooling.xml` |
| 2 | 17.322 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.xml` |
| 3 | 11.988 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit-unit-scripts-tooling.xml` |
| 4 | 10.945 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 5 | 10.759 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-unit-scripts-tooling.xml` |
| 6 | 10.126 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.xml` |
| 7 | 10.102 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_tolerates_unavailable_remote_main_baseline_builder` | `junit-unit-scripts-tooling.xml` |
| 8 | 10.019 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.xml` |
| 9 | 9.509 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 10 | 8.287 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 11 | 7.271 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 12 | 7.205 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestListAvailablePipelinesFunction::test_matches_registry_list` | `junit.unit-other.xml` |
| 13 | 6.906 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.xml` |
| 14 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.xml` |
| 15 | 5.577 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 16 | 4.844 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 17 | 4.833 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 18 | 4.767 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.xml` |
| 19 | 4.254 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_token_warnings_stay_on_stderr[Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 -Purpose 'test MCP'-OPTIONAL_TOKEN is not set for test MCP]` | `junit-repo-backed-unit.xml` |
| 20 | 4.138 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_exposes_shared_chembl_policy_surfaces` | `junit-contract-confidence.xml` |
| 21 | 4.136 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `junit-contract-confidence.xml` |
| 22 | 4.118 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `junit-contract-confidence.xml` |
| 23 | 4.1 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.xml` |
| 24 | 4.008 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.xml` |
| 25 | 3.999 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 4 | 47.748 | 21.002 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 47.569 | 17.322 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 13.864 | 8.287 |
| 4 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 12.392 | 4.138 |
| 5 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.945 | 10.945 |
| 6 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.509 | 9.509 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.271 | 7.271 |
| 8 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestListAvailablePipelinesFunction` | 1 | 7.205 | 7.205 |
| 9 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 6.906 | 6.906 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.004 | 6.004 |

