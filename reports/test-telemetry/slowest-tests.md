# Slowest Tests

Source commit: `57bd29902c233bcec8c2a56282e7f276a5d2f100`
Source run id: `local-pr12270-current`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34495`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 28.757 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 2 | 19.975 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 17.356 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 4 | 16.198 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 5 | 15.268 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 6 | 14.518 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 7 | 13.038 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 8 | 11.809 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-target]` | `integration.xml` |
| 9 | 11.141 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | 11.091 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 10.963 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[absolute-target]` | `integration.xml` |
| 12 | 10.831 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 13 | 10.805 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 14 | 10.767 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 15 | 10.487 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 16 | 10.121 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 17 | 9.799 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |
| 18 | 9.213 | `tests.contract.test_chembl_case_and_ontology_consistency::test_chembl_ontology_identifier_families_are_profile_and_matrix_aligned[profile0-chembl_assay-bao_format-bao:0000190-BAO_0000190]` | `contract-confidence.xml` |
| 19 | 8.531 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-target]` | `integration.xml` |
| 20 | 8.526 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `integration.xml` |
| 21 | 7.878 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 22 | 6.949 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-publication]` | `integration.xml` |
| 23 | 6.842 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-publication]` | `integration.xml` |
| 24 | 6.802 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 25 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 7 | 72.249 | 17.356 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 61.77 | 28.757 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.598 | 10.831 |
| 4 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 16.198 | 16.198 |
| 5 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 15.268 | 15.268 |
| 6 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 14.518 | 14.518 |
| 7 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.141 | 11.141 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.091 | 11.091 |
| 9 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 10.805 | 10.805 |
| 10 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.487 | 10.487 |

