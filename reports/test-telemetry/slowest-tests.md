# Slowest Tests

Source commit: `886f1db27e2bc7af6fdee2750bef89565dbc5ef2`
Source run id: `local-pr12115-validated-coverage`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `33935`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 37.121 | `tests.integration.infrastructure.quarantine.test_unified_quarantine_partition::test_inspect_reads_legacy_nonpartitioned_table` | `integration.xml` |
| 2 | 26.97 | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[None]` | `unit-scripts-tooling-other.xml` |
| 3 | 18.749 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 14.928 | `tests.unit.application.composite.test_dependency_key_resolvers.TestChainedKeyResolver::test_falls_back_to_seed_on_empty_table` | `unit-application.xml` |
| 5 | 12.632 | `tests.unit.application.test_main_module::test_main_block_executed_via_subprocess` | `unit-application.xml` |
| 6 | 11.728 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 7 | 11.616 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 8 | 11.366 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 9 | 11.318 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 10 | 11.245 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 11 | 11.172 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 12 | 11.087 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 13 | 11.068 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 14 | 11.029 | `tests.integration.infrastructure.quarantine.test_unified_quarantine_partition::test_replay_and_purge_on_legacy_nonpartitioned_table` | `integration.xml` |
| 15 | 10.606 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 16 | 10.281 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `unit-other.xml` |
| 17 | 10.113 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 18 | 9.138 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 19 | 8.422 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 20 | 8.364 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 21 | 8.236 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 22 | 8.158 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 23 | 7.754 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 24 | 7.644 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 25 | 7.619 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory::test_direct_module_entrypoint_help_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.infrastructure.quarantine.test_unified_quarantine_partition` | 2 | 48.15 | 37.121 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 39.949 | 18.749 |
| 3 | `tests.unit.scripts.ops.observability.test_green_acceptance` | 1 | 26.97 | 26.97 |
| 4 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.563 | 11.318 |
| 5 | `tests.unit.application.composite.test_dependency_key_resolvers.TestChainedKeyResolver` | 1 | 14.928 | 14.928 |
| 6 | `tests.unit.application.test_main_module` | 1 | 12.632 | 12.632 |
| 7 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.728 | 11.728 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.616 | 11.616 |
| 9 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 11.366 | 11.366 |
| 10 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 11.172 | 11.172 |

