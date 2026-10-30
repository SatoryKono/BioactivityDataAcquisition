# Slowest Tests

Source commit: `35e4c0a9a3a649d43b211c0efc5696c87dd13aed`
Source run id: `41106532481`
Source event: `workflow_dispatch`
Source run URL: `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/41106532481`
Refresh status: `captured`
Executed test cases: `62803`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 32.892 | `tests.unit.scripts.engineering.ci.test_pr_lane_results::test_shadow_compare_keeps_package_discovery_contract_narrow` | `junit-unit-scripts-tooling.other.xml` |
| 2 | 11.307 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `junit.integration.xml` |
| 3 | 10.889 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `junit.integration.xml` |
| 4 | 10.657 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `junit-repo-backed-unit.ops.xml` |
| 5 | 10.646 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `junit.integration.xml` |
| 6 | 10.511 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `junit.integration.xml` |
| 7 | 10.436 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `junit.integration.xml` |
| 8 | 10.125 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit.unit-infrastructure.xml` |
| 9 | 10.013 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `junit-unit-scripts-tooling.other.xml` |
| 10 | 8.472 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_real_pytest_partition_and_daily_missing_node_fail_closed` | `junit-unit-scripts-tooling.other.xml` |
| 11 | 8.176 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `junit.integration.xml` |
| 12 | 7.738 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_cli_unavailable_fails_closed_with_redacted_report` | `junit-repo-backed-unit.ops.xml` |
| 13 | 7.216 | `tests.security.test_security.TestInputValidation::test_no_eval_or_exec_in_source` | `junit.security.xml` |
| 14 | 7.099 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `junit.unit-other.xml` |
| 15 | 6.756 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `junit-repo-backed-unit.product.xml` |
| 16 | 6.722 | `tests.performance.test_measure_merger_input::test_measurement_harness_smoke` | `junit-serial-coverage.xml` |
| 17 | 6.722 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `junit.integration.xml` |
| 18 | 6.441 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `junit-unit-scripts-tooling.passport.xml` |
| 19 | 6.366 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestFactoryValidity::test_all_factories_have_pipeline_name` | `junit.unit-other.xml` |
| 20 | 6.046 | `tests.unit.composition.bootstrap.runtime.test_composite_contract_evidence::test_composite_archive_bootstrap_imports_in_fresh_process` | `junit.unit-other.xml` |
| 21 | 6.004 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `junit-unit-scripts-tooling.other.xml` |
| 22 | 5.707 | `tests.unit.scripts.engineering.ci.test_pytest_abort_diagnostic_adapter::test_no_fallback_skips_second_pass_after_timeout` | `junit-unit-scripts-tooling.other.xml` |
| 23 | 5.567 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `junit.integration.xml` |
| 24 | 5.195 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection::test_ordinary_observability_inventory_does_not_read_generated_reports` | `junit-unit-scripts-tooling.other.xml` |
| 25 | 5.008 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `junit-fast.unit-infrastructure.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.engineering.ci.test_pr_lane_results` | 1 | 32.892 | 32.892 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.157 | 10.646 |
| 3 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery` | 2 | 18.395 | 10.657 |
| 4 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter` | 2 | 15.133 | 10.125 |
| 5 | `tests.unit.scripts.engineering.ci.test_generated_artifact_selection` | 2 | 13.667 | 8.472 |
| 6 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.307 | 11.307 |
| 7 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 10.889 | 10.889 |
| 8 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.436 | 10.436 |
| 9 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 10.013 | 10.013 |
| 10 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 8.176 | 8.176 |
