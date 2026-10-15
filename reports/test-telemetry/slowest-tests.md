# Slowest Tests

Source commit: `3bb4a9fca5636f2bda77a4730090d10ffe07650a`
Source run id: `local-pr12204-combined-3bb4a9fc`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `33963`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 36.754 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 2 | 33.633 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 3 | 23.594 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 4 | 20.771 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | 12.614 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 12.328 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 7 | 11.564 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | 11.284 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 9 | 11.197 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 10 | 11.17 | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[None]` | `unit-scripts-tooling-other.xml` |
| 11 | 11.023 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 12 | 10.973 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 13 | 10.938 | `tests.security.test_security.TestVCRCassetteSanitization::test_no_authorization_headers_with_real_values[Authorization]` | `security.xml` |
| 14 | 10.809 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 15 | 10.658 | `tests.unit.composition.runtime_builders.test_runner_builder_profiles::test_build_pipeline_runner_persists_manifest_before_empty_cached_bronze_fail` | `unit-other.xml` |
| 16 | 10.469 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 17 | 9.866 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_powershell_uv_resolver_candidate_paths[function Get-Command { param($Name, $ErrorAction) if ($Name -eq 'uvx') { [pscustomobject]@{Source='C:\\fake\\uvx.exe'} } }\nfunction Test-Path { param($LiteralPath, $Path, $ErrorAction) $LiteralPath -eq 'C:\\fake\\uvx.exe' }\nfunction Resolve-Path { param($LiteralPath) [pscustomobject]@{Path=$LiteralPath} }-C:\\fake\\uvx.exe]` | `repo-backed-unit-tooling.xml` |
| 18 | 9.762 | `tests.unit.scripts.docs.passports.test_passport_path_renamer::test_migration_dry_run_apply_and_check_are_idempotent` | `unit-scripts-tooling-passport.xml` |
| 19 | 9.411 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 20 | 9.38 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 21 | 8.947 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli::test_direct_module_entrypoint_json_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 22 | 8.407 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 23 | 8.231 | `tests.unit.repo_backed.scripts.ai.test_npm_runtime_contract::test_both_setup_platforms_enforce_preinstall_contract` | `repo-backed-unit-tooling.xml` |
| 24 | 8.008 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 25 | 7.648 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 45.713 | 20.771 |
| 2 | `tests.integration.test_runtime_metric_emission_consistency` | 1 | 36.754 | 36.754 |
| 3 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 1 | 33.633 | 33.633 |
| 4 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 23.594 | 23.594 |
| 5 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.782 | 10.973 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.564 | 11.564 |
| 7 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 11.284 | 11.284 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.197 | 11.197 |
| 9 | `tests.unit.scripts.ops.observability.test_green_acceptance` | 1 | 11.17 | 11.17 |
| 10 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 11.023 | 11.023 |

