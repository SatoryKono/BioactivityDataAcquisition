# Slowest Tests

Source commit: `33b01a42162fd153edbebc2f2b61b9fcf1764dcd`
Source run id: `local-bioetl-local-coverage-pr11990-final`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33537`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 168.519 | `tests.unit.interfaces.cli.test_workflow_cli::test_multi_pipeline_push_failure_preserves_success_and_report` | `unit-other.xml` |
| 2 | 97.292 | `tests.unit.tools.test_opencode_agent_header::test_agent_contains_canonical_core[bugfix.md]` | `unit-other.xml` |
| 3 | 51.07 | `tests.integration.adapters.test_uniprot_idmapping.TestUniProtIDMappingIntegration::test_map_single_id` | `integration.xml` |
| 4 | 31.359 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 5 | 25.797 | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 6 | 20.009 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 7 | 17.781 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 8 | 15.92 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 15.623 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-target]` | `integration.xml` |
| 10 | 14.759 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-publication]` | `integration.xml` |
| 11 | 13.107 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `unit-scripts-tooling-other.xml` |
| 12 | 12.115 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 13 | 11.916 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-molecule]` | `integration.xml` |
| 14 | 11.762 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 15 | 11.605 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-target]` | `integration.xml` |
| 16 | 11.573 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-activity]` | `integration.xml` |
| 17 | 11.392 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |
| 18 | 11.161 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 19 | 10.944 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 20 | 10.917 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 21 | 10.847 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 22 | 10.449 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-publication]` | `integration.xml` |
| 23 | 9.735 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 24 | 9.679 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 25 | 9.582 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.interfaces.cli.test_workflow_cli` | 1 | 168.519 | 168.519 |
| 2 | `tests.unit.tools.test_opencode_agent_header` | 1 | 97.292 | 97.292 |
| 3 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 8 | 96.899 | 15.623 |
| 4 | `tests.integration.adapters.test_uniprot_idmapping.TestUniProtIDMappingIntegration` | 1 | 51.07 | 51.07 |
| 5 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 35.334 | 15.92 |
| 6 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 31.359 | 31.359 |
| 7 | `tests.unit.infrastructure.export.test_export_adapters` | 1 | 25.797 | 25.797 |
| 8 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.861 | 10.944 |
| 9 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.009 | 20.009 |
| 10 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation` | 1 | 17.781 | 17.781 |

