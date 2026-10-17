# Slowest Tests

Source commit: `badcaeb5d30892e9356969342a14403990794201`
Source run id: `local-bioetl-local-coverage-badcaeb-r2`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34094`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 208.818 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline::test_legacy_only_refresh_rejects_before_overwriting_baseline` | `unit-scripts-tooling-other.xml` |
| 2 | 93.182 | `tests.unit.scripts.ops.observability.test_green_optional_inputs::test_absent_optional_child_requires_verified_empty_input[None]` | `unit-scripts-tooling-other.xml` |
| 3 | 45.829 | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[None]` | `unit-scripts-tooling-other.xml` |
| 4 | 27.247 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard::test_architecture_quality_scorecard_has_stable_weighted_shape` | `unit-infrastructure.xml` |
| 5 | 27.237 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 6 | 20.884 | `tests.unit.application.services.dq.test_silver_statistics_helpers.TestSilverStatisticsHelpers::test_profile_categorical_column_builds_top_values` | `unit-application.xml` |
| 7 | 18.436 | `tests.unit.application.services.dq.test_silver_statistics_helpers.TestSilverStatisticsHelpers::test_profile_numeric_column_returns_distribution_for_non_empty_values` | `unit-application.xml` |
| 8 | 18.228 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 18.133 | `tests.unit.infrastructure.storage.silver_writer.test_silver_writer_lineage.TestSilverWriterCsvExport::test_write_silver_with_csv_exporter` | `unit-filesystem-contracts.xml` |
| 10 | 17.777 | `tests.unit.scripts.ai.test_prompt_library::test_check_registry_ok` | `unit-scripts-tooling-other.xml` |
| 11 | 17.286 | `tests.unit.scripts.ai.test_update_deepwiki::test_real_repo_wiki_is_consistent` | `unit-scripts-tooling-other.xml` |
| 12 | 16.916 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 13 | 16.046 | `tests.unit.scripts.ai.mcp.test_export_mcp_env_from_dotenv.TestExportMcpEnvFromDotenv::test_user_scope_flag_accepted` | `unit-scripts-tooling-other.xml` |
| 14 | 15.831 | `tests.unit.scripts.ci.test_test_telemetry_provenance::test_accepts_equal_inputs_and_confirmed_squash_tree` | `unit-scripts-tooling-other.xml` |
| 15 | 15.287 | `tests.unit.scripts.ops.observability.test_grafana_acceptance_provenance::test_fixed_window_reaches_url_and_immutable_manifest` | `unit-scripts-tooling-other.xml` |
| 16 | 15.11 | `tests.unit.scripts.ops.observability.test_grafana_acceptance_provenance::test_partial_render_preserves_success_and_failure` | `unit-scripts-tooling-other.xml` |
| 17 | 12.579 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 18 | 11.499 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 19 | 11.461 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 20 | 11.444 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 21 | 11.303 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 22 | 11.262 | `tests.unit.helpers.test_vcr_config_fixture_routing::test_every_in_tree_vcr_config_fixture_routes_through_base_helper` | `unit-other.xml` |
| 23 | 10.872 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 24 | 10.796 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 25 | 10.757 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.ci.test_update_test_telemetry_baseline` | 1 | 208.818 | 208.818 |
| 2 | `tests.unit.scripts.ops.observability.test_green_optional_inputs` | 1 | 93.182 | 93.182 |
| 3 | `tests.unit.scripts.ops.observability.test_green_acceptance` | 1 | 45.829 | 45.829 |
| 4 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 41.188 | 18.228 |
| 5 | `tests.unit.application.services.dq.test_silver_statistics_helpers.TestSilverStatisticsHelpers` | 2 | 39.32 | 20.884 |
| 6 | `tests.unit.scripts.ops.observability.test_grafana_acceptance_provenance` | 2 | 30.397 | 15.287 |
| 7 | `tests.unit.infrastructure.quality.test_architecture_quality_scorecard` | 1 | 27.247 | 27.247 |
| 8 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 27.237 | 27.237 |
| 9 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.668 | 10.872 |
| 10 | `tests.unit.infrastructure.storage.silver_writer.test_silver_writer_lineage.TestSilverWriterCsvExport` | 1 | 18.133 | 18.133 |

