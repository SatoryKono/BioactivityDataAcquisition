# Slowest Tests

Source commit: `9881f0306235c957086bed9a6c2faf7b38714e01`
Source run id: `34235189753`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34235189753`
Refresh status: `captured`
Collected test cases: `49936`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 23.398 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 2 | 17.099 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 3 | 11.117 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 4 | 10.618 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_token_warnings_stay_on_stderr[Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 -Purpose 'test MCP'-OPTIONAL_TOKEN is not set for test MCP]` | `junit-repo-backed-unit.tooling.xml` |
| 5 | 10.043 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 6 | 9.935 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 7 | 9.101 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 8 | 7.312 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 9 | 7.253 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 10 | 7.161 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 11 | 7.16 | `tests.unit.composition.test_registry_protocol.TestPipelineRegistryUnifiedAPI::test_list_keys_returns_list` | `junit.unit-other.xml` |
| 12 | 6.619 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_fetch_wrapper_executes_resolved_uvx` | `junit-repo-backed-unit.tooling.xml` |
| 13 | 6.537 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 14 | 6.252 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 15 | 6.137 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 16 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 17 | 5.56 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 18 | 4.776 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 4.616 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 20 | 4.155 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 4.043 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 3.946 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_release_review_freshness_gate_passes_for_recent_live_review` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 23 | 3.93 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit-unit-scripts-tooling.other.xml` |
| 24 | 3.925 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `junit-contract-confidence.xml` |
| 25 | 3.914 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit-unit-scripts-tooling.other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 41.023 | 17.099 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 34.515 | 23.398 |
| 3 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 2 | 17.237 | 10.618 |
| 4 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 12.389 | 6.252 |
| 5 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 11.887 | 4.043 |
| 6 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.101 | 9.101 |
| 7 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.312 | 7.312 |
| 8 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.253 | 7.253 |
| 9 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.161 | 7.161 |
| 10 | `tests.unit.composition.test_registry_protocol.TestPipelineRegistryUnifiedAPI` | 1 | 7.16 | 7.16 |

