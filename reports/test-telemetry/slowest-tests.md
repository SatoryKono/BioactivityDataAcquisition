# Slowest Tests

Source commit: `c09e776cecd2d0df98d1babf4bcc01109bdf985e`
Source run id: `local-pr-12268-final`
Source event: `local_coverage_verify`
Source run URL: `pending`
Refresh status: `captured`
Executed test cases: `34482`
Executed counts non-skipped JUnit records, including zero or missing
duration; duplicate identities remain separate records. This is not a
collection count. Older CI timed-row totals are not directly comparable.
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 15.18 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-scripts-tooling-debt-governance.xml` |
| 2 | 11.215 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline::test_chembl_activity_happy_path` | `integration.xml` |
| 3 | 11.036 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline::test_chembl_target_component_happy_path` | `integration.xml` |
| 4 | 10.499 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_source_fields` | `integration.xml` |
| 5 | 10.484 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline::test_chembl_cell_line_happy_path` | `integration.xml` |
| 6 | 10.442 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline::test_chembl_compound_record_happy_path` | `integration.xml` |
| 7 | 9.444 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact` | `unit-scripts-tooling-debt-governance.xml` |
| 8 | 9.072 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale` | `unit-scripts-tooling-debt-governance.xml` |
| 9 | 7.275 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_assay_replay_compares_physical_production_outputs` | `integration.xml` |
| 10 | 6.448 | `tests.unit.scripts.qa.test_check_quality_exemptions::test_check_quality_exemptions_passes_current_zero_budget_registry` | `unit-scripts-tooling-other.xml` |
| 11 | 6.216 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage::test_tracked_fixture_run_persists_linked_control_plane_artifacts` | `integration.xml` |
| 12 | 6.003 | `tests.unit.scripts.ops.test_recover_renderer::test_check_only_suggests_recover` | `unit-scripts-tooling-other.xml` |
| 13 | 5.824 | `tests.unit.infrastructure.test_issue_10469_stream_a_infra_thirteen.TestExemptionsDebtReductionAndFormatter::test_exemptions_policy_outside_src_and_required_registry_shapes` | `unit-infrastructure.xml` |
| 14 | 5.488 | `tests.unit.composition.factories.pipeline.test_registry::test_registry_completeness` | `unit-other.xml` |
| 15 | 5.432 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `repo-backed-unit-product.xml` |
| 16 | 5.385 | `tests.unit.scripts.docs.passports.test_passport_projector::test_workflow_operations_are_classified` | `unit-scripts-tooling-passport.xml` |
| 17 | 5.294 | `tests.integration.composite.test_assay_snapshot_merge_replay::test_other_composite_families_replay_physical_outputs[relative-capture-target]` | `integration.xml` |
| 18 | 5.234 | `tests.unit.composition.factories.pipeline.test_registry_consistency.TestRegistryNameUniqueness::test_registry_has_unique_names` | `unit-other.xml` |
| 19 | 5.022 | `tests.unit.scripts.engineering.ci.test_pytest_abort_diagnostic_adapter::test_no_fallback_skips_second_pass_after_timeout` | `unit-scripts-tooling-other.xml` |
| 20 | 4.765 | `tests.contract.test_provider_contract_drift_replay::test_provider_contract_replay_cases_do_not_break[openalex:works_search_endpoint]` | `contract-confidence.xml` |
| 21 | 4.464 | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[true]` | `unit-scripts-tooling-other.xml` |
| 22 | 4.406 | `tests.unit.scripts.qa.test_generate_semantic_pipeline_audit::test_build_current_member_facts_exposes_composite_inherited_field_types` | `unit-scripts-tooling-other.xml` |
| 23 | 4.231 | `tests.unit.scripts.ops.observability.test_green_acceptance::test_live_child_restores_production_http_and_durability[None]` | `unit-scripts-tooling-other.xml` |
| 24 | 4.057 | `tests.integration.application.core.test_cf_medallion_strict_wiring::test_all_shipped_pipeline_configs_preserve_partitions_and_pass_preflight` | `integration.xml` |
| 25 | 3.946 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `contract-confidence.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.qa.test_report_debt_governance_gates` | 3 | 33.696 | 15.18 |
| 2 | `tests.integration.pipelines.test_chembl_cell_line.TestChemblCellLinePipeline` | 2 | 20.983 | 10.499 |
| 3 | `tests.integration.composite.test_assay_snapshot_merge_replay` | 2 | 12.569 | 7.275 |
| 4 | `tests.integration.pipelines.test_chembl_activity.TestChemblActivityPipeline` | 1 | 11.215 | 11.215 |
| 5 | `tests.integration.pipelines.test_chembl_target_component.TestChemblTargetComponentPipeline` | 1 | 11.036 | 11.036 |
| 6 | `tests.integration.pipelines.test_chembl_compound_record.TestChemblCompoundRecordPipeline` | 1 | 10.442 | 10.442 |
| 7 | `tests.unit.scripts.ops.observability.test_green_acceptance` | 2 | 8.695 | 4.464 |
| 8 | `tests.unit.scripts.qa.test_check_quality_exemptions` | 1 | 6.448 | 6.448 |
| 9 | `tests.integration.ci.test_track_d_fixture_control_plane_linkage` | 1 | 6.216 | 6.216 |
| 10 | `tests.unit.scripts.ops.test_recover_renderer` | 1 | 6.003 | 6.003 |

