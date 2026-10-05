# Slowest Tests

Source commit: `d57aae4056ac05458ecf12658433169e23583995`
Source run id: `local-rf023-coverage-d57aae40-utf8`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `32979`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 72.888 | `tests.integration.test_dashboard_ux_report_freshness::test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link` | `integration.xml` |
| 2 | 52.714 | `tests.unit.composition.test_workflow_cohort_lineage::test_real_gold_expiry_descendant_and_partial_resume_keep_scoped_history[None]` | `unit-other.xml` |
| 3 | 50.7 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 4 | 47.011 | `tests.contract.schemas.test_pubchem_shard_validation::test_pubchem_identity_shard_accepts_minimal_valid_row` | `contract-confidence.xml` |
| 5 | 36.019 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 27.549 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `unit-other.xml` |
| 7 | 20.014 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 8 | 17.328 | `tests.unit.composition.runtime_builders.test_runner_builder_profiles::test_build_pipeline_runner_persists_manifest_before_empty_cached_bronze_fail` | `unit-other.xml` |
| 9 | 12.624 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 10 | 12.424 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 12.333 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[target]` | `integration.xml` |
| 12 | 12.054 | `tests.unit.scripts.qa.test_generate_architecture_debt_tasks::test_generate_architecture_debt_tasks_script_writes_payload` | `unit-scripts-tooling-other.xml` |
| 13 | 11.844 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 14 | 11.726 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[activity]` | `integration.xml` |
| 15 | 11.681 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 16 | 11.43 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 17 | 11.257 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 18 | 11.172 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 19 | 11.019 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 20 | 10.721 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 21 | 10.532 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 22 | 9.603 | `tests.integration.config.test_validate_pipeline_configs::test_validate_config_tree_reports_missing_workflow_pipeline_reference` | `integration.xml` |
| 23 | 9.546 | `tests.unit.domain.schemas.test_primary_key_unique::test_target_protein_classification_rejects_duplicate_entity_id` | `unit-domain.xml` |
| 24 | 9.356 | `tests.integration.infrastructure.storage.test_silver_merge_replay::test_silver_merge_replay_is_idempotent_by_table_checksum` | `integration.xml` |
| 25 | 9.11 | `tests.integration.infrastructure.storage.test_deterministic_write.TestDeterministicCsvFilterRead::test_csv_filter_reader_returns_sorted_tuple` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.test_dashboard_ux_report_freshness` | 1 | 72.888 | 72.888 |
| 2 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 58.706 | 36.019 |
| 3 | `tests.unit.composition.test_workflow_cohort_lineage` | 1 | 52.714 | 52.714 |
| 4 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 50.7 | 50.7 |
| 5 | `tests.contract.schemas.test_pubchem_shard_validation` | 1 | 47.011 | 47.011 |
| 6 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 3 | 36.683 | 12.624 |
| 7 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence` | 1 | 27.549 | 27.549 |
| 8 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.191 | 11.172 |
| 9 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.014 | 20.014 |
| 10 | `tests.unit.composition.runtime_builders.test_runner_builder_profiles` | 1 | 17.328 | 17.328 |

