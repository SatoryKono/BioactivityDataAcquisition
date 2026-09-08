# Slowest Tests

Source commit: `6391d86a41cd1359c4624a4d03b998dad88fd6eb`
Source run id: `34206477644`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34206477644`
Refresh status: `captured`
Collected test cases: `49882`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 17.627 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | 10.925 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | 10.449 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 4 | 10.379 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 5 | 8.177 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 6 | 7.303 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 7 | 7.2 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 8 | 7.177 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 9 | 7.011 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 10 | 6.073 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 11 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 12 | 5.373 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 13 | 5.229 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration::test_bootstrapped_service_can_list_pipelines` | `junit.unit-other.xml` |
| 14 | 4.817 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 15 | 4.745 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.other.xml` |
| 16 | 4.598 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_token_warnings_stay_on_stderr[Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 -Purpose 'test MCP'-OPTIONAL_TOKEN is not set for test MCP]` | `junit-repo-backed-unit.tooling.xml` |
| 17 | 4.574 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 18 | 4.068 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 4.017 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 3.973 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_release_review_freshness_gate_passes_for_recent_live_review` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 21 | 3.904 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 3.9 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 3.813 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `junit-repo-backed-unit.ops.xml` |
| 24 | 3.781 | `tests.integration.config.test_chembl_contract_registry_coverage::test_chembl_registry_fixture_and_contract_surfaces_stay_in_dynamic_parity` | `junit.integration.xml` |
| 25 | 3.682 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `junit-repo-backed-unit.ops.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 42.428 | 17.627 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 18.42 | 10.925 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.25 | 8.177 |
| 4 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 11.872 | 4.068 |
| 5 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.303 | 7.303 |
| 6 | `tests.unit.scripts.docs.passports.test_passport_projector` | 1 | 7.2 | 7.2 |
| 7 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.177 | 7.177 |
| 8 | `tests.contract.test_provider_contract_drift_replay` | 1 | 7.011 | 7.011 |
| 9 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.005 | 6.005 |
| 10 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 5.373 | 5.373 |

