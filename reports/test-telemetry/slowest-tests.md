# Slowest Tests

Source commit: `06c589f92f9f22f88a6b9bcdde07e68a8b34d9dd`
Source run id: `local-local-coverage-pr13248-v3`
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
| 1 | 35.806 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes::test_runtime_evidence_selects_owning_contract[tests/helpers/runtime_acceptance_12553.py]` | `unit-scripts-tooling-other.xml` |
| 2 | 19.237 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 3 | 18.281 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 16.806 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 5 | 15.129 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 6 | 14.457 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `security.xml` |
| 7 | 13.605 | `tests.unit.scripts.engineering.ci.test_pytest_receipts::test_xdist_waits_for_slow_worker_receipt_finalization` | `unit-scripts-tooling-other.xml` |
| 8 | 12.563 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 9 | 11.921 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 10 | 11.475 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected::test_nightly_shadow_changes_keep_both_archive_and_inventory_owners[scripts/engineering/ci/nightly_shadow_archive.py]` | `unit-scripts-tooling-other.xml` |
| 11 | 11.31 | `tests.unit.scripts.ops.observability.test_overview_global_alerts::test_generator_rebuilds_global_alerts_without_changing_saved_run_queries` | `unit-scripts-tooling-other.xml` |
| 12 | 11.177 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_routes_quality_move_governance_inputs` | `unit-scripts-tooling-other.xml` |
| 13 | 11.163 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 14 | 11.057 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 15 | 10.881 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `serial.xml` |
| 16 | 10.789 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 17 | 10.74 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 18 | 10.718 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 19 | 10.647 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 20 | 10.066 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `unit-scripts-tooling-other.xml` |
| 21 | 9.749 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_have_runtime_emitters` | `integration.xml` |
| 22 | 9.57 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 23 | 8.901 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_baseline_memory_routes::test_unreviewed_peers_still_fail_alone_and_beside_reviewed_paths[configs/quality/external_resource_inventory_unknown_review.json]` | `unit-scripts-tooling-other.xml` |
| 24 | 8.728 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected::test_owned_hook_python_inputs_keep_real_bounded_test_owners` | `unit-scripts-tooling-other.xml` |
| 25 | 8.599 | `tests.unit.scripts.test_hook_installation::test_real_owned_hooks_protocol_and_foreign_callback_once[False-None]` | `unit-scripts-tooling-other.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 39.646 | 18.281 |
| 2 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_runtime_acceptance_routes` | 1 | 35.806 | 35.806 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.846 | 11.057 |
| 4 | `tests.unit.scripts.engineering.ci.test_pr_lane_results_affected` | 2 | 20.203 | 11.475 |
| 5 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 1 | 19.237 | 19.237 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 16.806 | 16.806 |
| 7 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 15.129 | 15.129 |
| 8 | `tests.security.test_security.TestInputValidation` | 1 | 14.457 | 14.457 |
| 9 | `tests.unit.scripts.engineering.ci.test_pytest_receipts` | 1 | 13.605 | 13.605 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 12.563 | 12.563 |
