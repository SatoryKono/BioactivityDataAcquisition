# Slowest Tests

Source commit: `4964755e33a54280bade6a30b1f1f52460cac7d1`
Source run id: `34138902302`
Source event: `pull_request`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/34138902302`
Refresh status: `captured`
Collected test cases: `49776`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 17.735 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 2 | 10.899 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 3 | 10.576 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 4 | 10.409 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 5 | 9.045 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `junit-contract-confidence.xml` |
| 6 | 8.145 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 7 | 7.289 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 8 | 7.005 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 9 | 6.671 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 10 | 6.492 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit-track-d.xml` |
| 11 | 6.335 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestListAvailablePipelinesFunction::test_matches_registry_list` | `junit.unit-other.xml` |
| 12 | 6.003 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 13 | 5.517 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_script_runs_without_errors` | `junit-unit-scripts-tooling.other.xml` |
| 14 | 5.442 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 15 | 5.435 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 16 | 4.858 | `tests.integration.config.test_chembl_dq_catalog_sync::test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows` | `junit.integration.xml` |
| 17 | 4.771 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `junit-contract-confidence.xml` |
| 18 | 4.108 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_release_review_freshness_gate_passes_for_recent_live_review` | `junit-unit-scripts-tooling.debt-governance.xml` |
| 19 | 3.981 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `junit-contract-confidence.xml` |
| 20 | 3.911 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `junit.integration.xml` |
| 21 | 3.877 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `junit-contract-confidence.xml` |
| 22 | 3.82 | `tests.integration.config.test_chembl_contract_registry_coverage::test_chembl_registry_fixture_and_contract_surfaces_stay_in_dynamic_parity` | `junit.integration.xml` |
| 23 | 3.813 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_exposes_shared_chembl_policy_surfaces` | `junit-contract-confidence.xml` |
| 24 | 3.696 | `tests.contract.test_chembl_case_and_ontology_consistency::test_chembl_ontology_identifier_families_are_profile_and_matrix_aligned[profile0-chembl_assay-bao_format-bao:0000190-BAO_0000190]` | `junit-contract-confidence.xml` |
| 25 | 3.657 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `junit-unit-scripts-tooling.other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 4 | 42.828 | 17.735 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 16.341 | 10.899 |
| 3 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 2 | 14.637 | 8.145 |
| 4 | `tests.contract.test_normalization_cross_layer_contracts` | 3 | 11.671 | 3.981 |
| 5 | `tests.contract.test_provider_contract_drift_replay` | 1 | 9.045 | 9.045 |
| 6 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 7.289 | 7.289 |
| 7 | `tests.unit.composition.factories.pipeline.test_registry` | 1 | 7.005 | 7.005 |
| 8 | `tests.unit.scripts.docs.passports.test_passport_projector` | 1 | 6.671 | 6.671 |
| 9 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestListAvailablePipelinesFunction` | 1 | 6.335 | 6.335 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.003 | 6.003 |

