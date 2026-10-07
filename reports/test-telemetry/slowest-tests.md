# Slowest Tests

Source commit: `adc0c0aff4ae04588d5221f5e1de4bf97d52f8d9`
Source run id: `local-coverage`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33325`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 42.524 | `tests.integration.test_runtime_metric_emission_consistency::test_critical_observability_metric_families_are_runtime_emitted` | `integration.xml` |
| 2 | 37.679 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 3 | 29.249 | `tests.integration.test_dashboard_ux_report_freshness::test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link` | `integration.xml` |
| 4 | 20.009 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 5 | 18.179 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 13.004 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `security.xml` |
| 7 | 12.932 | `tests.security.test_security.TestPathTraversal::test_config_files_use_safe_paths` | `security.xml` |
| 8 | 11.626 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 9 | 11.597 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 10 | 11.157 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 11 | 11.016 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 12 | 10.467 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 13 | 10.251 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 14 | 10.06 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 15 | 9.837 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 16 | 8.595 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 17 | 8.142 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 18 | 7.839 | `tests.security.test_security.TestVCRCassetteSanitization::test_no_authorization_headers_with_real_values[Authorization]` | `security.xml` |
| 19 | 7.3 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `unit-other.xml` |
| 20 | 7.232 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 21 | 7.202 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 22 | 7.029 | `tests.security.test_exception_redaction::test_structured_exception_context_redacts_hostile_nested_secrets` | `security.xml` |
| 23 | 7.027 | `tests.security.test_dq_report_xss_prevention::test_html_report_escapes_check_names` | `security.xml` |
| 24 | 6.937 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 25 | 6.529 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 49.276 | 37.679 |
| 2 | `tests.integration.test_runtime_metric_emission_consistency` | 1 | 42.524 | 42.524 |
| 3 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 38.076 | 18.179 |
| 4 | `tests.integration.test_dashboard_ux_report_freshness` | 1 | 29.249 | 29.249 |
| 5 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.009 | 20.009 |
| 6 | `tests.security.test_security.TestInputValidation` | 1 | 13.004 | 13.004 |
| 7 | `tests.security.test_security.TestPathTraversal` | 1 | 12.932 | 12.932 |
| 8 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.626 | 11.626 |
| 9 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.157 | 11.157 |
| 10 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 11.016 | 11.016 |

