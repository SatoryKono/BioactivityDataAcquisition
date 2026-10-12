# Slowest Tests

Source commit: `c52c681ed5586950f1d054585455690100d9875a`
Source run id: `local-pr12187-main-d124-20261012`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33496`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 22.181 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 2 | 21.064 | `tests.security.test_security.TestVCRCassetteSanitization::test_no_authorization_headers_with_real_values[Authorization]` | `security.xml` |
| 3 | 20.019 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 4 | 19.066 | `tests.unit.infrastructure.observability.test_tracing.TestTracingImportFallbackBranches::test_module_marks_otlp_unavailable_when_exporter_import_fails` | `unit-infrastructure.xml` |
| 5 | 18.65 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 6 | 17.779 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 7 | 17.245 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 8 | 16.08 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 12.764 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 10 | 12.457 | `tests.integration.test_dashboard_ux_report_freshness::test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link` | `integration.xml` |
| 11 | 12.293 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 12 | 11.24 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 13 | 10.838 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 14 | 10.697 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 15 | 10.534 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 16 | 10.497 | `tests.integration.test_grafana_render_first_remediation::test_scrolling_capture_preserves_layout_viewport` | `integration.xml` |
| 17 | 10.374 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 18 | 10.36 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-publication]` | `integration.xml` |
| 19 | 10.226 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 20 | 9.154 | `tests.unit.infrastructure.observability.test_tracing_port_contract.TestTracingPortContract::test_noop_tracing_span_path_is_safe` | `unit-infrastructure.xml` |
| 21 | 8.437 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-molecule]` | `integration.xml` |
| 22 | 8.397 | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[structlog]` | `smoke.xml` |
| 23 | 8.039 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |
| 24 | 7.655 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 25 | 7.214 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 36.68 | 16.08 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 28.617 | 17.779 |
| 3 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 3 | 26.452 | 10.36 |
| 4 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 22.181 | 22.181 |
| 5 | `tests.security.test_security.TestVCRCassetteSanitization` | 1 | 21.064 | 21.064 |
| 6 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.019 | 20.019 |
| 7 | `tests.unit.infrastructure.observability.test_tracing.TestTracingImportFallbackBranches` | 1 | 19.066 | 19.066 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 18.65 | 18.65 |
| 9 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 17.748 | 10.534 |
| 10 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 17.245 | 17.245 |

