# Slowest Tests

Source commit: `57cf7da119faffe8a395629ed9fe6b4f7be40f73`
Source run id: `local-bioetl-local-coverage-57cf7da`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34037`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 43.733 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline::test_legacy_only_refresh_rejects_before_overwriting_baseline` | `unit-scripts-tooling-other.xml` |
| 2 | 23.839 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 13.892 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 11.548 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 5 | 11.507 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 11.415 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 7 | 11.062 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 8 | 11.021 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 9 | 10.828 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 10 | 10.526 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 11 | 10.374 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 12 | 10.215 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 13 | 10.042 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli::test_direct_module_entrypoint_json_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 14 | 9.308 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 15 | 7.778 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 16 | 7.611 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 17 | 7.554 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 18 | 7.35 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 19 | 7.349 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `contract-confidence.xml` |
| 20 | 7.308 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |
| 21 | 7.272 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 22 | 7.119 | `tests.contract.test_chembl_case_and_ontology_consistency::test_chembl_ontology_identifier_families_are_profile_and_matrix_aligned[profile0-chembl_assay-bao_format-bao:0000190-BAO_0000190]` | `contract-confidence.xml` |
| 23 | 6.884 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `integration.xml` |
| 24 | 6.875 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 25 | 6.55 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 49.238 | 23.839 |
| 2 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline` | 1 | 43.733 | 43.733 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.89 | 11.062 |
| 4 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.548 | 11.548 |
| 5 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.415 | 11.415 |
| 6 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 11.021 | 11.021 |
| 7 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 1 | 10.526 | 10.526 |
| 8 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 10.374 | 10.374 |
| 9 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 10.215 | 10.215 |
| 10 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli` | 1 | 10.042 | 10.042 |

