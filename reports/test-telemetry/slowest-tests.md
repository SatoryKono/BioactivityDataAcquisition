# Slowest Tests

Source commit: `dc61bfdfc64606fad502dfb369dc6c15eff995d5`
Source run id: `local-local-verify-pr12096-20261009-final6`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Collected test cases: `33458`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 230.123 | `tests.unit.application.services.run_reports.test_composite_report::test_damaged_child_report_cannot_produce_success_message[wrong_identity]` | `unit-application.xml` |
| 2 | 35.382 | `tests.unit.infrastructure.export.test_export_adapters::test_write_pack_records_successful_xlsx_artifact` | `unit-infrastructure.xml` |
| 3 | 32.024 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 4 | 27.687 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-publication]` | `integration.xml` |
| 5 | 26.643 | `tests.smoke.test_smoke.TestRuntimeDependencies::test_runtime_dependency_importable[yaml]` | `smoke.xml` |
| 6 | 25.484 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders::test_bash_keeps_openai_and_openrouter_credentials_separate` | `repo-backed-unit-tooling.xml` |
| 7 | 22.62 | `tests.smoke.test_smoke.TestCoreImports::test_composition_imports` | `smoke.xml` |
| 8 | 20.018 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_filter_options_deadline_does_not_send_late_success` | `unit-other.xml` |
| 9 | 19.778 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-molecule]` | `integration.xml` |
| 10 | 18.808 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-target]` | `integration.xml` |
| 11 | 17.787 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-publication]` | `integration.xml` |
| 12 | 16.18 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 13 | 16.152 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_authority_shim_types` | `unit-scripts-tooling-other.xml` |
| 14 | 14.813 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-target]` | `integration.xml` |
| 15 | 14.558 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-both-activity]` | `integration.xml` |
| 16 | 14.139 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-molecule]` | `integration.xml` |
| 17 | 12.222 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-molecule]` | `integration.xml` |
| 18 | 11.052 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 19 | 10.745 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 20 | 10.723 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 21 | 10.638 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 22 | 10.594 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-replay-activity]` | `integration.xml` |
| 23 | 10.482 | `tests.unit.repo_backed.scripts.ops.docker.test_restart_docker_recovery::test_last_resort_requires_switch_and_should_process_confirmation` | `repo-backed-unit-ops.xml` |
| 24 | 9.724 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 25 | 9.641 | `tests.unit.infrastructure.observability.test_tracing.TestTracingImportFallbackBranches::test_module_marks_otlp_unavailable_when_exporter_import_fails` | `unit-infrastructure.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.application.services.run_reports.test_composite_report` | 1 | 230.123 | 230.123 |
| 2 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 9 | 150.386 | 27.687 |
| 3 | `tests.unit.infrastructure.export.test_export_adapters` | 1 | 35.382 | 35.382 |
| 4 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 1 | 32.024 | 32.024 |
| 5 | `tests.smoke.test_smoke.TestRuntimeDependencies` | 1 | 26.643 | 26.643 |
| 6 | `tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders` | 1 | 25.484 | 25.484 |
| 7 | `tests.smoke.test_smoke.TestCoreImports` | 1 | 22.62 | 22.62 |
| 8 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 21.468 | 10.745 |
| 9 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 20.018 | 20.018 |
| 10 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 16.18 | 16.18 |

