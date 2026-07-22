# Slowest Tests

Source commit: `460eb53be1`
Source run id: `local-pre-ci-issues-6392-6401-20260722`
Refresh status: `captured`
Collected test cases: `11721`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 12.016 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers::test_processed_records_distinguishes_empty_and_backend_unavailable` | `unit-parallel-safe.xml` |
| 2 | 5.874 | `tests.architecture.test_config_discrepancy_report_drift::test_config_discrepancy_report_matches_deterministic_generator` | `architecture-current-change.xml` |
| 3 | 4.581 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_gate_rejects_cross_occurrence_source_artifacts` | `unit-parallel-safe.xml` |
| 4 | 4.264 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_gate_rejects_render_source_without_valid_panel_scope[empty_panel_states]` | `unit-parallel-safe.xml` |
| 5 | 3.826 | `tests.contract.test_gold_entity_coverage_complete::test_each_gold_entity_is_strict_with_published_contract[chembl_activity]` | `serial-maintained.xml` |
| 6 | 3.618 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures::test_cached_populated_isolated_registry_contains_pipeline_factories` | `serial-maintained.xml` |
| 7 | 3.4 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_gate_rejects_render_source_without_valid_panel_scope[missing]` | `unit-parallel-safe.xml` |
| 8 | 3.086 | `tests.unit.domain.schemas.openalex.test_publication_schema.TestOpenAlexPublicationSchema::test_year_range_validation` | `unit-parallel-safe.xml` |
| 9 | 2.451 | `tests.contract.test_gold_pk_consistency.TestGoldPkConsistency::test_pipeline_configs_use_new_pk_naming` | `serial-maintained.xml` |
| 10 | 2.381 | `tests.unit.scripts.test_report_observability_metric_inventory::test_collect_metric_inventory_records_static_prometheus_collector_emitters` | `unit-parallel-safe.xml` |
| 11 | 2.316 | `tests.unit.scripts.test_report_observability_metric_inventory::test_collect_metric_inventory_detects_runtime_metric_without_registry` | `unit-parallel-safe.xml` |
| 12 | 2.303 | `tests.contract.test_normalization_cross_layer_contracts::test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope` | `serial-maintained.xml` |
| 13 | 2.242 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_audit_cycle_runs_preflight_rerender_and_live_audit` | `unit-parallel-safe.xml` |
| 14 | 2.149 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle::test_grafana_audit_cycle_keeps_render_gate_after_semantic_preflight_failure` | `unit-parallel-safe.xml` |
| 15 | 2.082 | `tests.unit.scripts.qa.test_run_observability_closure_campaign::test_execute_returns_nonzero_when_campaign_is_incomplete` | `unit-parallel-safe.xml` |
| 16 | 2.036 | `tests.security.test_security.TestNoHardcodedSecrets::test_no_hardcoded_secrets__no_hardcoded_secrets__bd2bd2d3` | `serial-maintained.xml` |
| 17 | 2.023 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_pipeline_normalization_field_matrix_1223__c8b0b2c2` | `serial-maintained.xml` |
| 18 | 1.975 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible` | `serial-maintained.xml` |
| 19 | 1.958 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_activity_meta_passthrough_contract_is_aligned_across_profile_matrix_and_processor` | `serial-maintained.xml` |
| 20 | 1.938 | `tests.unit.scripts.qa.test_run_observability_closure_campaign::test_execute_then_finalize_writes_complete_report_only_when_every_gate_is_satisfied` | `unit-parallel-safe.xml` |
| 21 | 1.9 | `tests.contract.test_normalization_cross_layer_contracts::test_chembl_activity_business_and_set_like_fields_follow_profile_family_contracts` | `serial-maintained.xml` |
| 22 | 1.89 | `tests.unit.scripts.qa.test_report_debt_governance_gates::test_build_payload__missing_flaky_review__fails_gate_without_crashing` | `unit-parallel-safe.xml` |
| 23 | 1.888 | `tests.unit.composition.bootstrap.test_runner_bootstrap.TestBootstrapPipelineRunnerServiceIntegration::test_bootstrapped_service_can_list_pipelines` | `bootstrap.xml` |
| 24 | 1.816 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix::test_build_field_matrix_rows_covers_entity_profile_and_generic_rules` | `serial-maintained.xml` |
| 25 | 1.79 | `tests.unit.domain.schemas.openalex.test_publication_schema.TestOpenAlexPublicationSchema::test_citations_made_non_negative` | `unit-parallel-safe.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.unit.scripts.ops.observability.test_grafana_dashboard_audit_cycle` | 5 | 16.636 | 4.581 |
| 2 | `tests.unit.interfaces.http.test_health_server_routing_pure_helpers` | 1 | 12.016 | 12.016 |
| 3 | `tests.contract.test_normalization_cross_layer_contracts` | 4 | 8.136 | 2.303 |
| 4 | `tests.architecture.test_config_discrepancy_report_drift` | 1 | 5.874 | 5.874 |
| 5 | `tests.unit.domain.schemas.openalex.test_publication_schema.TestOpenAlexPublicationSchema` | 2 | 4.876 | 3.086 |
| 6 | `tests.unit.scripts.test_report_observability_metric_inventory` | 2 | 4.697 | 2.381 |
| 7 | `tests.unit.scripts.qa.test_run_observability_closure_campaign` | 2 | 4.02 | 2.082 |
| 8 | `tests.unit.repo_backed.scripts.test_generate_pipeline_normalization_field_matrix` | 2 | 3.839 | 2.023 |
| 9 | `tests.contract.test_gold_entity_coverage_complete` | 1 | 3.826 | 3.826 |
| 10 | `tests.unit.repo_backed.composition.test_bootstrap_cache_fixtures` | 1 | 3.618 | 3.618 |

