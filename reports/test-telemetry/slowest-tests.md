# Slowest Tests

Source commit: `f54cda4a0f3361a3581a00fa79c03ec18c242171`
Source run id: `local-local-coverage-pr12234-f54cda4a0f3361a3581a00fa79c03ec18c242171`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34038`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 49.396 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 31.868 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 3 | 22.014 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 19.888 | `tests.unit.application.composite.test_merger.TestDeduplicateEnricher::test_no_duplicates_returns_unchanged` | `unit-application.xml` |
| 5 | 17.422 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli::test_direct_module_entrypoint_json_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 6 | 17.297 | `tests.unit.repo_backed.scripts.ai.mcp.test_wrappers::test_catalog_has_unique_safe_wrapper_bindings` | `repo-backed-unit-tooling.xml` |
| 7 | 16.722 | `tests.unit.application.test_issue_10469_one_line_residuals::test_composite_join_preserves_shared_right_key` | `unit-application.xml` |
| 8 | 13.687 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 13.218 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 10 | 12.193 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 11 | 12.179 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 12 | 12.166 | `tests.security.test_security.TestVCRCassetteSanitization::test_no_authorization_headers_with_real_values[Authorization]` | `security.xml` |
| 13 | 12.149 | `tests.unit.application.composite.test_merger.TestDeduplicateEnricher::test_identical_values_preserves_type` | `unit-application.xml` |
| 14 | 12.07 | `tests.security.test_security.TestPathTraversal::test_config_files_use_safe_paths` | `security.xml` |
| 15 | 11.445 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 16 | 11.444 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 17 | 11.278 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 18 | 11.001 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 19 | 10.547 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 20 | 9.454 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 21 | 8.319 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |
| 22 | 8.273 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 23 | 8.139 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 24 | 7.965 | `tests.smoke.test_smoke.TestDevDependencies::test_dev_dependency_importable[hypothesis]` | `smoke.xml` |
| 25 | 7.516 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 49.396 | 49.396 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 47.146 | 22.014 |
| 3 | `tests.unit.application.composite.test_merger.TestDeduplicateEnricher` | 2 | 32.037 | 19.888 |
| 4 | `tests.integration.test_runtime_metric_emission_consistency` | 1 | 31.868 | 31.868 |
| 5 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 23.18 | 12.179 |
| 6 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli` | 1 | 17.422 | 17.422 |
| 7 | `tests.unit.repo_backed.scripts.ai.mcp.test_wrappers` | 1 | 17.297 | 17.297 |
| 8 | `tests.unit.application.test_issue_10469_one_line_residuals` | 1 | 16.722 | 16.722 |
| 9 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 13.218 | 13.218 |
| 10 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 12.193 | 12.193 |

