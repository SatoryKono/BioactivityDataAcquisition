# Slowest Tests

Source commit: `846fd4a709a3263de820fd2f3787cf75fabaaf7b`
Source run id: `local-p02-r6-coverage-846fd4a7-r6`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33379`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 75.21 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[activity]` | `integration.xml` |
| 2 | 43.705 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 3 | 30.113 | `tests.integration.application.core.test_write_outcome_loss_integration::test_silver_schema_quarantine_persists_real_records` | `integration.xml` |
| 4 | 21.422 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 5 | 20.719 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 20.007 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 7 | 13.653 | `tests.integration.composite.test_column_naming_integration.TestMultipleEnrichers::test_three_providers_merge_correctly` | `integration.xml` |
| 8 | 13.634 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 12.176 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 10 | 11.802 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 11 | 11.507 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 12 | 11.502 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 13 | 11.167 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 14 | 10.925 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 15 | 10.856 | `tests.integration.composite.test_composite_cross_validation::test_composite_cross_validation_flags_field_mismatch` | `integration.xml` |
| 16 | 10.77 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 17 | 9.787 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 18 | 9.699 | `tests.integration.adapters.openalex.test_adapter.TestOpenAlexAdapterIntegration::test_fetch_filtered_by_doi` | `integration.xml` |
| 19 | 9.405 | `tests.unit.repo_backed.scripts.test_report_observability_metric_inventory_cli::test_direct_module_entrypoint_json_bootstraps_without_circular_import` | `repo-backed-unit-tooling.xml` |
| 20 | 9.398 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 21 | 9.263 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 22 | 9.235 | `tests.integration.infrastructure.quarantine.test_unified_quarantine_partition_layout::test_replay_and_purge_on_legacy_nonpartitioned_table` | `integration.xml` |
| 23 | 8.987 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 24 | 8.669 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 25 | 8.478 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 2 | 84.473 | 75.21 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 55.775 | 21.422 |
| 3 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 43.705 | 43.705 |
| 4 | `tests.integration.application.core.test_write_outcome_loss_integration` | 1 | 30.113 | 30.113 |
| 5 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.427 | 11.502 |
| 6 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 20.845 | 12.176 |
| 7 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.007 | 20.007 |
| 8 | `tests.integration.composite.test_column_naming_integration.TestMultipleEnrichers` | 1 | 13.653 | 13.653 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.802 | 11.802 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 11.507 | 11.507 |

