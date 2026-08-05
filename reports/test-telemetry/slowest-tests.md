# Slowest Tests

Source commit: `77342c98ea9cff99d19aaa9805efdb7ce05b5a34`
Source run id: `local-duration-rebuild-2026-07-23`
Refresh status: `captured`
Collected test cases: `46742`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 22.399 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit.unit-other.xml` |
| 2 | 11.55 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit.unit-other.xml` |
| 3 | 11.315 | `tests.unit.scripts.docs.passports.test_passport_projector::test_cli_generate_and_check` | `junit-fast.xml` |
| 4 | 10.797 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_subprocess_environment_invariant` | `junit.unit-other.xml` |
| 5 | 10.615 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.xml` |
| 6 | 7.251 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generated_facts_validate_against_published_schemas` | `junit.unit-other.xml` |
| 7 | 6.817 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 8 | 6.505 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration::test_bootstrapped_service_can_list_pipelines` | `junit.unit-other.xml` |
| 9 | 6.126 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 10 | 5.529 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit.unit-other.xml` |
| 11 | 5.235 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_fetch_wrapper_executes_resolved_uvx` | `junit-repo-backed-unit.xml` |
| 12 | 5.086 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit.unit-other.xml` |
| 13 | 4.746 | `tests.unit.scripts.test_normalization_governance_cli_smoke::test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke` | `junit.unit-other.xml` |
| 14 | 4.669 | `tests.unit.scripts.docs.passports.test_passport_projector::test_generation_is_byte_deterministic` | `junit-fast.xml` |
| 15 | 4.285 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit.unit-other.xml` |
| 16 | 4.27 | `tests.unit.scripts.docs.passports.test_passport_projector::test_schema_rejects_unknown_nested_keys_and_incompatible_version` | `junit.unit-other.xml` |
| 17 | 4.258 | `tests.unit.scripts.docs.passports.test_passport_projector::test_source_refs_exist_and_metric_labels_are_bounded` | `junit.unit-other.xml` |
| 18 | 4.148 | `tests.unit.scripts.docs.passports.test_passport_projector::test_pipeline_markdown_is_compact_complete_and_not_a_json_dump` | `junit.unit-other.xml` |
| 19 | 4.111 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_writes_deterministic_artifacts` | `junit.unit-other.xml` |
| 20 | 4.083 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_returns_non_zero_when_fallback_business_budget_is_exceeded` | `junit.unit-other.xml` |
| 21 | 4.081 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory::test_main_accepts_current_fallback_business_budget` | `junit.unit-other.xml` |
| 22 | 4.044 | `tests.unit.scripts.docs.passports.test_passport_projector::test_duplicate_audit_reports_compaction` | `junit.unit-other.xml` |
| 23 | 4.0 | `tests.integration.interfaces.test_cli_run_dry_run.TestCliRunDryRun::test_dry_run_option_available` | `junit.integration.xml` |
| 24 | 4.0 | `tests.unit.scripts.docs.passports.test_passport_projector::test_representative_pipeline_projection_profiles_are_explicit` | `junit.unit-other.xml` |
| 25 | 3.969 | `tests.integration.interfaces.test_cli_run_incremental.TestCliRunIncremental::test_run_help_displays_options` | `junit.integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.docs.passports.test_passport_projector` | 12 | 92.986 | 22.399 |
| 2 | `tests.unit.scripts.qa.test_report_normalization_fallback_inventory` | 3 | 12.275 | 4.111 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.615 | 10.615 |
| 4 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 6.817 | 6.817 |
| 5 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration` | 1 | 6.505 | 6.505 |
| 6 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.126 | 6.126 |
| 7 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv` | 1 | 5.529 | 5.529 |
| 8 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 1 | 5.235 | 5.235 |
| 9 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit` | 1 | 5.086 | 5.086 |
| 10 | `tests.unit.scripts.test_normalization_governance_cli_smoke` | 1 | 4.746 | 4.746 |

