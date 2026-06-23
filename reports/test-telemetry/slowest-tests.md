# Slowest Tests

Source commit: `281a0ed48ad70bb108fb90ada50a6a6cdd77f409`
Source run id: `local-current-main-telemetry-20260623`
Refresh status: `captured`
Collected test cases: `8507`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 42.785 | `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage::test_checkpoint_compatibility_runtime_facade_is_not_used_in_tests` | `S7-crosscutting-architecture-a2.xml` |
| 2 | 28.12 | `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage::test_checkpoint_compatibility_runtime_facade_is_not_used_in_src` | `S7-crosscutting-architecture-a2.xml` |
| 3 | 24.051 | `tests.architecture.test_config_discrepancy_metrics_ratchets::test_config_discrepancy_baseline_matches_live_generator` | `S7-crosscutting-architecture-a2.xml` |
| 4 | 23.018 | `tests.architecture.test_config_discrepancy_report_drift::test_config_discrepancy_report_matches_deterministic_generator` | `S7-crosscutting-architecture-a2.xml` |
| 5 | 21.493 | `tests.unit.composition.runtime_builders.test_runner_builder_runtime_modes::test_build_pipeline_runner_uses_configured_mode_outside_test_mode` | `S2-comp-iface.xml` |
| 6 | 16.084 | `tests.architecture.test_cli_command_import_guards::test_non_cli_source_keeps_retained_public_cli_seams_outside_runtime_code` | `S7-crosscutting-architecture-a2.xml` |
| 7 | 15.28 | `tests.architecture.test_config_root_governance::test_runtime_config_discovery_does_not_use_source_parent_arithmetic` | `S7-crosscutting-architecture-a2.xml` |
| 8 | 14.498 | `tests.architecture.test_cli_command_import_guards::test_non_cli_source_avoids_interfaces_package_root_convenience_imports` | `S7-crosscutting-architecture-a2.xml` |
| 9 | 14.129 | `tests.architecture.test_adr_enforcement_matrix::test_adr_enforcement_matrix_artifact_matches_live_generator` | `S7-crosscutting-architecture-a.xml` |
| 10 | 13.15 | `tests.architecture.test_add_svg_text_fallback::test_build_fallback_text_emits_multiline_tspans` | `S7-crosscutting-architecture-a.xml` |
| 11 | 12.274 | `tests.architecture.test_compatibility_freeze_guards::test_cli_run_orchestration_singleton_stays_private_compat_owner` | `S7-crosscutting-architecture-a2.xml` |
| 12 | 11.328 | `tests.architecture.test_config_discrepancy_metrics_ratchets::test_config_discrepancy_metrics_within_scorecard_budget` | `S7-crosscutting-architecture-a2.xml` |
| 13 | 8.951 | `tests.architecture.test_adapter_contracts.TestAdapterMixinPolicy::test_src_does_not_import_legacy_adapter_mixin_modules` | `S7-crosscutting-architecture-a.xml` |
| 14 | 8.577 | `tests.architecture.test_contract_registry_loader_boundary::test_contract_registry_path_literal_is_confined_to_reviewed_surfaces` | `S7-crosscutting-architecture-a2.xml` |
| 15 | 8.48 | `tests.architecture.test_adapter_contracts.TestAdapterHealthCheck::test_adapters_have_health_check` | `S7-crosscutting-architecture-a.xml` |
| 16 | 8.158 | `tests.architecture.test_config_ci_invariants.TestEffectiveOptionalityResolution::test_resolved_optionality_matches_current_config_surface` | `S7-crosscutting-architecture-a2.xml` |
| 17 | 7.149 | `tests.architecture.test_config_ci_invariants.TestConfigFilesExist::test_runtime_config_primary_keys_match_contract_policy` | `S7-crosscutting-architecture-a2.xml` |
| 18 | 7.029 | `tests.architecture.test_config_surface_entity_residual_plateau::test_entity_residual_backlog_matches_live_metrics_and_scorecard` | `S7-crosscutting-architecture-a2.xml` |
| 19 | 6.109 | `tests.unit.domain.schemas.openalex.test_openalex_publication_validation.TestPmcIdBaseValidation::test_pmc_id_base_validation__id_invalid_format__d060aeb5[]` | `S1-domain-core.xml` |
| 20 | 5.742 | `tests.unit.composition.test_canonical_module_paths::test_execution_api_reexports_pipeline_runner_service` | `S2-comp-iface.xml` |
| 21 | 5.141 | `tests.architecture.test_adapter_contracts.TestAdapterPortCompliance::test_primary_adapter_classes_use_package_root_imports` | `S7-crosscutting-architecture-a.xml` |
| 22 | 5.019 | `tests.unit.interfaces.cli.commands.test_observability_backend_runtime::test_ensure_backend_fails_when_required_paths_never_become_ready` | `S2-comp-iface.xml` |
| 23 | 4.691 | `tests.architecture.test_config_surface_entity_residual_plateau::test_config_surface_duplication_audit_matches_live_backlog` | `S7-crosscutting-architecture-a2.xml` |
| 24 | 4.272 | `tests.unit.composition.bootstrap.test_bootstrap_entrypoints.TestBootstrapPipeline::test_bootstrap_pipeline_creates_runner_without_starting_server` | `S2-comp-iface.xml` |
| 25 | 3.464 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestRegistryConfigConsistency::test_all_registered_pipelines_have_config_files` | `S2-comp-iface.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage` | 2 | 70.905 | 42.785 |
| 2 | `tests.architecture.test_config_discrepancy_metrics_ratchets` | 2 | 35.379 | 24.051 |
| 3 | `tests.architecture.test_cli_command_import_guards` | 2 | 30.582 | 16.084 |
| 4 | `tests.architecture.test_config_discrepancy_report_drift` | 1 | 23.018 | 23.018 |
| 5 | `tests.unit.composition.runtime_builders.test_runner_builder_runtime_modes` | 1 | 21.493 | 21.493 |
| 6 | `tests.architecture.test_config_root_governance` | 1 | 15.28 | 15.28 |
| 7 | `tests.architecture.test_adr_enforcement_matrix` | 1 | 14.129 | 14.129 |
| 8 | `tests.architecture.test_add_svg_text_fallback` | 1 | 13.15 | 13.15 |
| 9 | `tests.architecture.test_compatibility_freeze_guards` | 1 | 12.274 | 12.274 |
| 10 | `tests.architecture.test_config_surface_entity_residual_plateau` | 2 | 11.72 | 7.029 |

