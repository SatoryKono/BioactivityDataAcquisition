# Slowest Tests

Source commit: `990793a7b506ef4baa42f7d450f8242e52d1cf8f`
Source run id: `local-local-coverage-pr13241-v3`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `41275`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 35.725 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `unit-scripts-tooling-other.xml` |
| 2 | 21.051 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 3 | 17.994 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 16.214 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 5 | 14.52 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 6 | 14.326 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 7 | 13.395 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `unit-scripts-tooling-other.xml` |
| 8 | 11.954 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 11.529 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected::test_nightly_shadow_changes_keep_both_archive_and_inventory_owners[scripts/engineering/ci/nightly_shadow_archive.py]` | `unit-scripts-tooling-other.xml` |
| 10 | 11.45 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 11 | 11.402 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 12 | 11.335 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 13 | 11.175 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 14 | 10.876 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 15 | 10.729 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 16 | 10.69 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `unit-scripts-tooling-other.xml` |
| 17 | 10.651 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `security.xml` |
| 18 | 10.527 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `unit-scripts-tooling-other.xml` |
| 19 | 10.201 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `serial.xml` |
| 20 | 10.152 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 21 | 9.843 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `integration.xml` |
| 22 | 9.598 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `unit-scripts-tooling-other.xml` |
| 23 | 8.965 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_monitoring_guide` | `unit-scripts-tooling-other.xml` |
| 24 | 8.781 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 25 | 8.683 | `tests.unit.iuphar_target_class.test_acceptance::test_filtered_child_cannot_publish_unexecuted_passes[]` | `unit-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.35 | 17.994 |
| 2 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 35.725 | 35.725 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.051 | 11.175 |
| 4 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 21.051 | 21.051 |
| 5 | `tests.unit.scripts.engineering.ci.test_pr_lane_results` | 2 | 19.492 | 10.527 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 16.214 | 16.214 |
| 7 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 14.52 | 14.52 |
| 8 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 14.326 | 14.326 |
| 9 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 13.395 | 13.395 |
| 10 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected` | 1 | 11.529 | 11.529 |
