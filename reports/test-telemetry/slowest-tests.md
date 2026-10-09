# Slowest Tests

Source commit: `0d9fcdb2e00725100eca9a52152c48c212c80fa6`
Source run id: `local-pr12164-final-0d9fcdb-w1-r2`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33475`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 75.696 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 2 | 35.443 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 3 | 33.504 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 4 | 27.111 | `tests.unit.domain.schemas.test_primary_key_unique::test_target_protein_classification_rejects_duplicate_entity_id` | `unit-domain.xml` |
| 5 | 20.018 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 6 | 19.111 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 7 | 19.055 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 8 | 18.201 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 9 | 16.9 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 10 | 16.346 | `tests.security.test_security.TestVCRCassetteSanitization::test_no_authorization_headers_with_real_values[Authorization]` | `security.xml` |
| 11 | 15.13 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 12 | 14.435 | `tests.unit.infrastructure.storage.silver_writer.test_silver_writer_lineage.TestSilverWriterCsvExport::test_write_silver_with_csv_exporter` | `unit-filesystem-contracts.xml` |
| 13 | 13.388 | `tests.unit.application.test_issue_10469_one_line_residuals::test_composite_join_preserves_shared_right_key` | `unit-application.xml` |
| 14 | 12.932 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 15 | 12.885 | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 16 | 12.848 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-target]` | `integration.xml` |
| 17 | 12.299 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-target]` | `integration.xml` |
| 18 | 12.149 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 19 | 12.11 | `tests.unit.scripts.repo.test_check_no_partial_tree::test_guard_flags_partial_tree_commit_in_range` | `unit-scripts-tooling-other.xml` |
| 20 | 11.278 | `tests.unit.application.test_main_module::test_main_block_executed_via_subprocess` | `unit-application.xml` |
| 21 | 10.947 | `tests.unit.domain.test_serialization.TestFlattenArrowTableForExport::test_flatten_list_columns` | `unit-domain.xml` |
| 22 | 10.797 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 23 | 10.762 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 24 | 10.693 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 25 | 10.547 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-publication]` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation` | 1 | 75.696 | 75.696 |
| 2 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 3 | 35.694 | 12.848 |
| 3 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 35.443 | 35.443 |
| 4 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 33.504 | 33.504 |
| 5 | `tests.unit.domain.schemas.test_primary_key_unique` | 1 | 27.111 | 27.111 |
| 6 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.559 | 10.797 |
| 7 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.018 | 20.018 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 19.111 | 19.111 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 19.055 | 19.055 |
| 10 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 18.201 | 18.201 |

