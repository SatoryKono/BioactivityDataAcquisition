# Slowest Tests

Source commit: `d4733848be9b69f07278d2f2be0fa1c346c2c8ec`
Source run id: `34124972115`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34124972115`
Refresh status: `captured`
Collected test cases: `49728`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 16.917 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | 10.986 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | 9.803 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 4 | 9.776 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 5 | 7.598 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 6 | 7.486 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 7 | 7.424 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 8 | 7.181 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 9 | 7.104 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 10 | 7.081 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 11 | 6.835 | `tests.unit.composition.test_registry_protocol.TestPipelineRegistryUnifiedAPI::test_list_keys_returns_list` | `junit.unit-other.xml` |
| 12 | 6.502 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 13 | 6.27 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 14 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 15 | 4.982 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.other.xml` |
| 16 | 4.419 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 17 | 4.061 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit-unit-scripts-tooling.other.xml` |
| 18 | 4.045 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_release_review_freshness_gate_passes_for_recent_live_review` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 19 | 4.045 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit-unit-scripts-tooling.other.xml` |
| 20 | 4.017 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 21 | 4.0 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 3.975 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 3.769 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `junit-repo-backed-unit.ops.xml` |
| 24 | 3.737 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 25 | 3.73 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `junit-repo-backed-unit.ops.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 40.541 | 16.917 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 4 | 26.083 | 10.986 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 13.756 | 7.486 |
| 4 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 12.036 | 4.061 |
| 5 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.424 | 7.424 |
| 6 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.181 | 7.181 |
| 7 | `tests.contract.test_provider_contract_drift_replay` | 1 | 7.104 | 7.104 |
| 8 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.081 | 7.081 |
| 9 | `tests.unit.composition.test_registry_protocol.TestPipelineRegistryUnifiedAPI` | 1 | 6.835 | 6.835 |
| 10 | `tests.unit.scripts.docs.passports.test_passport_projector` | 1 | 6.502 | 6.502 |

