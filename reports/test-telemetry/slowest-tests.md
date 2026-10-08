# Slowest Tests

Source commit: `3e734a6b872fff524c663cf183ade40aafdaea12`
Source run id: `local-cf-medallion-clock-strict-3e734a6b`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33362`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 54.535 | `tests.contract.test_composite_merge_golden::test_composite_merge_golden_seed_priority_is_stable` | `contract-confidence.xml` |
| 2 | 46.407 | `tests.unit.repo_backed.application.composite.test_merger_golden_snapshots::test_conflict_resolution_seed_priority_golden_snapshot` | `repo-backed-unit-product.xml` |
| 3 | 43.931 | `tests.smoke.test_control_plane_rollout_smoke::test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics` | `smoke.xml` |
| 4 | 35.115 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 5 | 25.086 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_prefers_uvx_on_path` | `repo-backed-unit-tooling.xml` |
| 6 | 20.017 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 7 | 15.458 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation::test_gold_snapshot_pins_version_and_distinguishes_physical_rows` | `unit-infrastructure.xml` |
| 8 | 15.174 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 13.009 | `tests.unit.repo_backed.scripts.ops.test_migrate_gold_parquet_to_delta::test_apply_preserves_rows_normalizes_metadata_and_is_idempotent` | `repo-backed-unit-ops.xml` |
| 10 | 11.421 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 11 | 11.28 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 12 | 11.166 | `tests.unit.repo_backed.application.composite.test_join_key_normalization::test_normalize_join_key_dataframe_columns_cleans_title_without_lowercase` | `repo-backed-unit-product.xml` |
| 13 | 11.105 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 14 | 11.057 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 15 | 10.911 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 16 | 10.404 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 17 | 10.342 | `tests.unit.repo_backed.application.composite.test_join_key_normalization::test_normalize_join_key_dataframe_columns_covers_supported_mutating_families` | `repo-backed-unit-product.xml` |
| 18 | 10.184 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_handles_unset_home` | `repo-backed-unit-tooling.xml` |
| 19 | 10.119 | `tests.unit.repo_backed.application.pipelines.chembl.test_activity_transformer.TestActivityTransformerSilverContract::test_transform_output_validates_with_stateful_activity_schema` | `repo-backed-unit-product.xml` |
| 20 | 9.553 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 21 | 9.358 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 22 | 9.341 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 23 | 8.111 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 24 | 7.791 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts::test_bash_uv_resolver_finds_uv_sibling` | `repo-backed-unit-tooling.xml` |
| 25 | 7.285 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.contract.test_composite_merge_golden` | 1 | 54.535 | 54.535 |
| 2 | `tests.unit.repo_backed.application.composite.test_merger_golden_snapshots` | 1 | 46.407 | 46.407 |
| 3 | `tests.smoke.test_control_plane_rollout_smoke` | 1 | 43.931 | 43.931 |
| 4 | `tests.unit.repo_backed.scripts.ai.mcp.test_mcp_wrapper_contracts` | 3 | 43.061 | 25.086 |
| 5 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders` | 1 | 35.115 | 35.115 |
| 6 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 33.873 | 15.174 |
| 7 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.968 | 11.057 |
| 8 | `tests.unit.repo_backed.application.composite.test_join_key_normalization` | 2 | 21.508 | 11.166 |
| 9 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.017 | 20.017 |
| 10 | `tests.unit.infrastructure.storage.test_workflow_foreign_key_reconciliation` | 1 | 15.458 | 15.458 |

