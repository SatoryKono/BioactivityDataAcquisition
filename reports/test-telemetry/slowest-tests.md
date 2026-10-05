# Slowest Tests

Source commit: `423ac2857da9094818cdb4ee815757a1c9e890db`
Source run id: `local-full-coverage-423ac28-resume`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `32863`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 64.282 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 50.809 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 3 | 44.826 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 4 | 41.743 | `tests.integration.test_dashboard_ux_report_freshness::test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link` | `integration.xml` |
| 5 | 39.323 | `tests.unit.composition.test_workflow_cohort_lineage::test_real_gold_expiry_descendant_and_partial_resume_keep_scoped_history[None]` | `unit-other.xml` |
| 6 | 35.105 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 7 | 23.414 | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 8 | 22.078 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 20.007 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 10 | 19.345 | `tests.integration.workflow.test_workflow_foreign_key_reconciliation::test_reconcile_foreign_keys_expires_gold_orphans_without_dropping_history` | `integration.xml` |
| 11 | 19.159 | `tests.security.test_exception_redaction::test_structured_exception_context_redacts_hostile_nested_secrets` | `security.xml` |
| 12 | 19.158 | `tests.security.test_dq_report_xss_prevention::test_html_report_escapes_check_names` | `security.xml` |
| 13 | 18.975 | `tests.integration.workflow.test_selected_snapshot_reconciliation::test_partial_and_total_deletion_preserve_other_runs_and_history[False-False]` | `integration.xml` |
| 14 | 14.3 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 15 | 14.078 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_ten.TestDeltaReaderAndTableOpsLeftovers::test_native_count_and_table_ops_concat` | `unit-infrastructure.xml` |
| 16 | 13.483 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 17 | 12.74 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 18 | 12.739 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 19 | 12.112 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 20 | 11.244 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 21 | 11.181 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 22 | 10.949 | `tests.unit.infrastructure.observability.test_tracing.TestTracingImportFallbackBranches::test_module_marks_otlp_unavailable_when_exporter_import_fails` | `unit-infrastructure.xml` |
| 23 | 10.917 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 24 | 10.828 | `tests.unit.scripts.ops.observability.test_grafana_acceptance_provenance::test_partial_render_preserves_success_and_failure` | `unit-scripts-tooling-other.xml` |
| 25 | 10.827 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 64.282 | 64.282 |
| 2 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation` | 1 | 50.809 | 50.809 |
| 3 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 46.929 | 22.078 |
| 4 | `tests.integration.test_runtime_metric_emission_consistency` | 1 | 44.826 | 44.826 |
| 5 | `tests.integration.test_dashboard_ux_report_freshness` | 1 | 41.743 | 41.743 |
| 6 | `tests.unit.composition.test_workflow_cohort_lineage` | 1 | 39.323 | 39.323 |
| 7 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders` | 1 | 35.105 | 35.105 |
| 8 | `tests.unit.infrastructure.export.test_export_adapters` | 1 | 23.414 | 23.414 |
| 9 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 22.425 | 11.244 |
| 10 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.007 | 20.007 |

