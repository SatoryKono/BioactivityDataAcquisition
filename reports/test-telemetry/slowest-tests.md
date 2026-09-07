# Slowest Tests

Source commit: `c18f737c3edc439e21ef8eaf2ebb6cd79060d01f`
Source run id: `34148282491`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34148282491`
Refresh status: `captured`
Collected test cases: `49802`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 13.408 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | 11.013 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | 8.491 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 4 | 7.957 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 5 | 7.807 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 6 | 7.666 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 7 | 7.329 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 8 | 7.292 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 9 | 7.266 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestRegistryNameUniqueness::test_registry_has_unique_names` | `junit.unit-other.xml` |
| 10 | 7.224 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 11 | 6.81 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 12 | 6.494 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 13 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 14 | 5.682 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 15 | 4.963 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_token_warnings_stay_on_stderr[Remove-Item Env:OPTIONAL_TOKEN -ErrorAction SilentlyContinue; Test-McpOptionalToken -Name 'OPTIONAL_TOKEN' -MinLength 8 -Purpose 'test MCP'-OPTIONAL_TOKEN is not set for test MCP]` | `junit-repo-backed-unit.tooling.xml` |
| 16 | 4.463 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.other.xml` |
| 17 | 4.247 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 18 | 3.891 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit-unit-scripts-tooling.other.xml` |
| 19 | 3.845 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 3.84 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_field_matrix__is_deterministic__61401586` | `junit-repo-backed-unit.tooling.xml` |
| 21 | 3.777 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `junit-repo-backed-unit.ops.xml` |
| 22 | 3.768 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `junit-repo-backed-unit.ops.xml` |
| 23 | 3.746 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.other.xml` |
| 24 | 3.744 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_check_artifacts_detects_drift__unit_scripts_test_generate_pipeline_normalization_field_matrix_1213` | `junit-repo-backed-unit.tooling.xml` |
| 25 | 3.733 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_pipeline_normalization_field_matrix_1223__c8b0b2c2` | `junit-repo-backed-unit.tooling.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 28.881 | 13.408 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 4 | 26.515 | 11.013 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 12.176 | 6.494 |
| 4 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 3 | 11.317 | 3.84 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 8.491 | 8.491 |
| 6 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 2 | 7.637 | 3.891 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.329 | 7.329 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.292 | 7.292 |
| 9 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestRegistryNameUniqueness` | 1 | 7.266 | 7.266 |
| 10 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.224 | 7.224 |

