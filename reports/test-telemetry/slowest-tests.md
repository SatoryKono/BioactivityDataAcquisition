# Slowest Tests

Source commit: `99ab9954a9ce05eef0265113b80073f3bb52168c`
Source run id: `33749109446`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/33749109446`
Refresh status: `captured`
Collected test cases: `49607`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 17.619 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | 10.791 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | 10.353 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 4 | 10.338 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 5 | 8.932 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 6 | 8.22 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 7 | 7.565 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestListAvailablePipelinesFunction::test_matches_registry_list` | `junit.unit-other.xml` |
| 8 | 7.204 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 9 | 7.088 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 10 | 6.979 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 11 | 6.91 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 12 | 6.032 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 13 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 14 | 5.016 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.other.xml` |
| 15 | 4.829 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 16 | 4.134 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_field_matrix__is_deterministic__61401586` | `junit-repo-backed-unit.tooling.xml` |
| 17 | 4.037 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.other.xml` |
| 18 | 4.024 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_pipeline_normalization_field_matrix_1223__c8b0b2c2` | `junit-repo-backed-unit.tooling.xml` |
| 19 | 4.01 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_check_artifacts_detects_drift__unit_scripts_test_generate_pipeline_normalization_field_matrix_1213` | `junit-repo-backed-unit.tooling.xml` |
| 20 | 3.985 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 3.98 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 22 | 3.968 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 3.957 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit-unit-scripts-tooling.other.xml` |
| 24 | 3.926 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_release_review_freshness_gate_passes_for_recent_live_review` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 25 | 3.873 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_build_field_matrix_rows_covers_entity_profile_and_generic_rules` | `junit-repo-backed-unit.tooling.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 42.236 | 17.619 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 19.723 | 10.791 |
| 3 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 4 | 16.041 | 4.134 |
| 4 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.252 | 8.22 |
| 5 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 11.91 | 3.985 |
| 6 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestListAvailablePipelinesFunction` | 1 | 7.565 | 7.565 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.204 | 7.204 |
| 8 | `tests.contract.test_provider_contract_drift_replay` | 1 | 7.088 | 7.088 |
| 9 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 6.979 | 6.979 |
| 10 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 6.91 | 6.91 |

