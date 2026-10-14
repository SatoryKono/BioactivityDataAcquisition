# Slowest Tests

Source commit: `6ba0e2803723369c2e4d48e4fdb320dcabaea63b`
Source run id: `local-bioetl-local-coverage-uiltn594`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33500`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 82.672 | `tests.unit.composition.test_workflow_cohort_lineage::test_real_gold_expiry_descendant_and_partial_resume_keep_scoped_history[None]` | `unit-other.xml` |
| 2 | 45.516 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 3 | 24.477 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 4 | 22.47 | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 5 | 20.221 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 20.008 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 7 | 19.721 | `tests.unit.application.services.dq.test_checks_integrity_extended.TestCheckSCDIntegrityExtended::test_overlapping_validity_periods_warn` | `unit-application.xml` |
| 8 | 16.902 | `tests.unit.infrastructure.adapters.test_csv_filter_reader.TestCsvFilterReaderLoadFilterIds::test_load_filter_ids_returns_filter_load_result` | `unit-infrastructure.xml` |
| 9 | 15.17 | `tests.unit.application.test_main_module::test_main_block_executed_via_subprocess` | `unit-application.xml` |
| 10 | 14.488 | `tests.unit.application.test_issue_10518_application_compwf_a::test_chained_key_filter_applied_and_failed` | `unit-application.xml` |
| 11 | 13.951 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 12 | 13.244 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 13 | 12.397 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 14 | 11.797 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 15 | 11.557 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 16 | 11.07 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 17 | 10.663 | `tests.integration.adapters.test_uniprot_idmapping.TestUniProtIDMappingIntegration::test_map_mixed_results` | `integration.xml` |
| 18 | 10.301 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |
| 19 | 10.05 | `tests.unit.application.composite.test_helper_module_coverage::test_cross_validator_helper_functions_cover_details_and_numeric_comparison` | `unit-application.xml` |
| 20 | 10.021 | `tests.unit.application.test_issue_10469_one_line_residuals::test_composite_join_preserves_shared_right_key` | `unit-application.xml` |
| 21 | 9.831 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 22 | 9.793 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 23 | 9.496 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 24 | 9.278 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 25 | 9.127 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.composition.test_workflow_cohort_lineage` | 1 | 82.672 | 82.672 |
| 2 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation` | 1 | 45.516 | 45.516 |
| 3 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 39.51 | 20.221 |
| 4 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 24.477 | 24.477 |
| 5 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 23.467 | 12.397 |
| 6 | `tests.unit.infrastructure.export.test_export_adapters` | 1 | 22.47 | 22.47 |
| 7 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.008 | 20.008 |
| 8 | `tests.unit.application.services.dq.test_checks_integrity_extended.TestCheckSCDIntegrityExtended` | 1 | 19.721 | 19.721 |
| 9 | `tests.unit.infrastructure.adapters.test_csv_filter_reader.TestCsvFilterReaderLoadFilterIds` | 1 | 16.902 | 16.902 |
| 10 | `tests.unit.application.test_main_module` | 1 | 15.17 | 15.17 |

