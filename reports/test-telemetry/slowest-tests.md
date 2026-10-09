# Slowest Tests

Source commit: `912f483953c76ede75313f762e41a9848369c3bb`
Source run id: `local-local-verify-pr12096-20261009-final16`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33462`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 20.009 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 2 | 17.172 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 3 | 11.118 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 4 | 11.101 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 5 | 11.02 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 6 | 10.801 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 7 | 10.742 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 8 | 10.726 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 9 | 10.463 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 10 | 10.38 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 11 | 9.332 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 12 | 8.036 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |
| 13 | 7.665 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 14 | 7.351 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 15 | 7.034 | `tests.integration.test_grafana_render_first_remediation::test_scrolling_capture_preserves_layout_viewport` | `integration.xml` |
| 16 | 6.434 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 17 | 6.32 | `tests.unit.scripts.test_pretest_guardrails_runtime::test_ci_architecture_reuse_requires_real_ci_evidence` | `unit-scripts-tooling-other.xml` |
| 18 | 6.318 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_diagnostic_subprocess_timeout_is_bounded` | `repo-backed-unit-ops.xml` |
| 19 | 6.307 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 20 | 6.178 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 21 | 6.005 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 22 | 5.959 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_bounded_restart_failure_uses_supported_stop_start_fallback` | `repo-backed-unit-ops.xml` |
| 23 | 5.939 | `tests.unit.helpers.test_vcr_config_fixture_routing::test_every_in_tree_vcr_config_fixture_routes_through_base_helper` | `unit-other.xml` |
| 24 | 5.883 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 25 | 5.668 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 38.572 | 17.172 |
| 2 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 3 | 22.74 | 10.463 |
| 3 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.468 | 10.742 |
| 4 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.009 | 20.009 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.118 | 11.118 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.101 | 11.101 |
| 7 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.801 | 10.801 |
| 8 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 1 | 9.332 | 9.332 |
| 9 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 1 | 8.036 | 8.036 |
| 10 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 7.665 | 7.665 |

