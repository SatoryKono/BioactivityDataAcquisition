# Slowest Tests

Source commit: `274609e20b8cf6a975e2ee80b91a933a655bd6f3`
Source run id: `local-duration-rebuild-2026-07-23`
Refresh status: `captured`
Collected test cases: `23360`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 192.078 | `tests.architecture.test_naming_ambiguity_classifier::test_build_ambiguity_groups_is_deterministic` | `S7-crosscutting-architecture-c.xml` |
| 2 | 76.218 | `tests.architecture.test_provider_registry_decomposition::test_private_default_registry_module_imports_stay_confined_to_sanctioned_seams` | `S7-crosscutting-architecture-c.xml` |
| 3 | 64.276 | `tests.architecture.test_debt_governance_telemetry_reporting::test_debt_governance_snapshot_matches_live_sources` | `S7-crosscutting-architecture-a3.xml` |
| 4 | 55.574 | `tests.architecture.test_provider_registry_decomposition::test_default_provider_registry_raw_calls_stay_confined_to_known_src_baseline` | `S7-crosscutting-architecture-c.xml` |
| 5 | 40.649 | `tests.architecture.test_quality_exemptions_registry::test_exemption_registry_targets_are_live` | `S7-crosscutting-architecture-c.xml` |
| 6 | 38.963 | `tests.architecture.test_naming_ambiguity_classifier::test_build_ambiguity_groups_reports_expected_ok_families` | `S7-crosscutting-architecture-c.xml` |
| 7 | 37.074 | `tests.architecture.test_mounted_worktree_skip_policy::test_tests_do_not_reintroduce_hardcoded_network_drive_skips` | `S7-crosscutting-architecture-c.xml` |
| 8 | 35.843 | `tests.architecture.test_private_module_imports::test_owner_aware_private_module_imports` | `S7-crosscutting-architecture-c.xml` |
| 9 | 35.412 | `tests.architecture.test_import_graph_invariants::test_import_graph_respects_layer_matrix` | `S7-crosscutting-architecture-b.xml` |
| 10 | 34.348 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `S8-crosscutting-governance.xml` |
| 11 | 33.691 | `tests.architecture.test_vcr_metadata_catalog_drift::test_vcr_metadata_catalog_tracks_cassettes_not_sidecars` | `S7-crosscutting-architecture-d.xml` |
| 12 | 31.733 | `tests.architecture.test_tech_debt_issues_5670_5675_closeout::test_issue_5674_internal_compatibility_shims_have_current_expiry_guards` | `S7-crosscutting-architecture-d.xml` |
| 13 | 30.766 | `tests.architecture.test_value_object_run_manifest_deprecation::test_deprecated_value_object_run_manifest_is_not_used_in_tests` | `S7-crosscutting-architecture-d.xml` |
| 14 | 29.077 | `tests.architecture.test_deterministic_sort_policy_coverage::test_entity_pipeline_sink_sort_policy_coverage_is_full` | `S7-crosscutting-architecture-a3.xml` |
| 15 | 29.051 | `tests.architecture.test_quality_exemptions_registry::test_exemption_registry_metadata_is_complete` | `S7-crosscutting-architecture-c.xml` |
| 16 | 28.619 | `tests.architecture.test_tech_debt_issues_5565_5569_closeout::test_issue_5566_semantic_seams_have_roles_and_no_new_src_callers` | `S7-crosscutting-architecture-d.xml` |
| 17 | 28.062 | `tests.architecture.test_naming_package_consistency_gate::test_consistency_gate_script_runs_clean_in_check_mode` | `S7-crosscutting-architecture-c.xml` |
| 18 | 26.574 | `tests.unit.composition.bootstrap.test_bootstrap_entrypoints.TestBootstrapPipeline::test_bootstrap_pipeline_creates_runner_without_starting_server` | `S2-comp-iface.xml` |
| 19 | 26.306 | `tests.integration.interfaces.test_cli_shutdown_integration.TestCliGracefulShutdownExitCode::test_shutdown_error_returns_exit_code_130` | `S5-infra-adapters.xml` |
| 20 | 26.301 | `tests.unit.interfaces.cli.test_cli_main_module.TestCliMainModule::test_module_runnable_with_help` | `S2-comp-iface.xml` |
| 21 | 26.227 | `tests.architecture.test_retirement_candidate_triage::test_repo_wide_zero_import_candidate_count_does_not_grow` | `S7-crosscutting-architecture-c.xml` |
| 22 | 26.086 | `tests.architecture.test_test_governance_audit::test_test_audit_closeout_2026_06_19_tracks_issue_pack_evidence` | `S7-crosscutting-architecture-d.xml` |
| 23 | 25.914 | `tests.unit.domain.test_exceptions.TestErrorClassifier::test_classify_unknown_exception` | `S1-domain-services.xml` |
| 24 | 25.571 | `tests.architecture.test_vcr_metadata_catalog_drift::test_vcr_metadata_catalog_drift_check_passes_current_repo` | `S7-crosscutting-architecture-d.xml` |
| 25 | 24.535 | `tests.unit.infrastructure.adapters.common.test_fetch_retry_policy::test_split_filter_ids_for_fallback_partition_property` | `S5-infra-adapters.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.architecture.test_naming_ambiguity_classifier` | 2 | 231.041 | 192.078 |
| 2 | `tests.architecture.test_provider_registry_decomposition` | 2 | 131.792 | 76.218 |
| 3 | `tests.architecture.test_quality_exemptions_registry` | 2 | 69.7 | 40.649 |
| 4 | `tests.architecture.test_debt_governance_telemetry_reporting` | 1 | 64.276 | 64.276 |
| 5 | `tests.architecture.test_vcr_metadata_catalog_drift` | 2 | 59.262 | 33.691 |
| 6 | `tests.architecture.test_mounted_worktree_skip_policy` | 1 | 37.074 | 37.074 |
| 7 | `tests.architecture.test_private_module_imports` | 1 | 35.843 | 35.843 |
| 8 | `tests.architecture.test_import_graph_invariants` | 1 | 35.412 | 35.412 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 34.348 | 34.348 |
| 10 | `tests.architecture.test_tech_debt_issues_5670_5675_closeout` | 1 | 31.733 | 31.733 |

