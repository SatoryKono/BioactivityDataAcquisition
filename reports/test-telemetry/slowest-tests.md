# Slowest Tests

Source commit: `ace4b794f81d2884fdc83fc22bf901324327dc74`
Source run id: `local-local-coverage-pr13244-v3`
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
| 1 | 34.676 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `unit-scripts-tooling-other.xml` |
| 2 | 19.335 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 3 | 18.329 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 16.014 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 5 | 15.246 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 6 | 14.5 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 7 | 13.624 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `unit-scripts-tooling-other.xml` |
| 8 | 13.035 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `security.xml` |
| 9 | 12.014 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | 11.762 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 11.274 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 12 | 11.165 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 13 | 10.84 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 14 | 10.745 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 15 | 10.683 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `unit-scripts-tooling-other.xml` |
| 16 | 10.667 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected::test_owned_hook_python_inputs_keep_real_bounded_test_owners` | `unit-scripts-tooling-other.xml` |
| 17 | 10.602 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_baseline_memory_routes::test_unreviewed_peers_still_fail_alone_and_beside_reviewed_paths[docs/plans/memory-recovery-unreviewed.md]` | `unit-scripts-tooling-other.xml` |
| 18 | 10.534 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 19 | 10.513 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `unit-scripts-tooling-other.xml` |
| 20 | 10.3 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected::test_nightly_shadow_changes_keep_both_archive_and_inventory_owners[scripts/engineering/ci/nightly_shadow_archive.py]` | `unit-scripts-tooling-other.xml` |
| 21 | 10.284 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `unit-scripts-tooling-other.xml` |
| 22 | 10.257 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `serial.xml` |
| 23 | 10.02 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `integration.xml` |
| 24 | 9.743 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 25 | 9.648 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_baseline_memory_routes::test_unreviewed_peers_still_fail_alone_and_beside_reviewed_paths[configs/quality/external_resource_inventory_unknown_review.json]` | `unit-scripts-tooling-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 44.103 | 18.329 |
| 2 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 34.676 | 34.676 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.91 | 11.165 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected` | 2 | 20.967 | 10.667 |
| 5 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_baseline_memory_routes` | 2 | 20.25 | 10.602 |
| 6 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 19.335 | 19.335 |
| 7 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 16.014 | 16.014 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 15.246 | 15.246 |
| 9 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 13.624 | 13.624 |
| 10 | `tests.security.test_security.TestInputValidation` | 1 | 13.035 | 13.035 |
