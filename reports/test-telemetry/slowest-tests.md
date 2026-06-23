# Slowest Tests

Source commit: `52353e5e833ce815c0d6c3a581405ce80f488471`
Source run id: `22890216064`
Refresh status: `captured`
Collected test cases: `14859`
Freshness guard: `<=45 days`

| Rank | Duration (s) | Test | Source |
|---:|---:|---|---|
| 1 | 19.186 | `tests.architecture.test_regression_metrics::test_mypy_error_count` | `junit_parallel.xml` |
| 2 | 15.867 | `tests.architecture.test_antipatterns::test_no_hardcoded_secrets` | `junit_parallel.xml` |
| 3 | 5.741 | `tests.unit.interfaces.cli.test_cli_main_module.TestCliMainModule::test_module_runnable_with_help` | `junit_parallel.xml` |
| 4 | 4.541 | `tests.unit.infrastructure.validation.test_pandera_validator.TestPanderaValidatorPropertyBased::test_noop_validators_always_return_valid` | `junit_parallel.xml` |
| 5 | 4.29 | `tests.architecture.test_test_structural_debt::test_no_test_functions_over_200_loc` | `junit_parallel.xml` |
| 6 | 4.204 | `tests.architecture.test_layer_dependencies::test_dead_code_vulture` | `junit_parallel.xml` |
| 7 | 4.108 | `tests.architecture.test_scripts_lifecycle_registry::test_scripts_lifecycle_registry_check_passes` | `junit_parallel.xml` |
| 8 | 4.051 | `tests.architecture.test_scripts_deprecation_backlog::test_scripts_deprecation_report_generation` | `junit_parallel.xml` |
| 9 | 3.948 | `tests.architecture.test_scripts_inventory_manifest::test_scripts_inventory_manifest_drift_check_passes` | `junit_parallel.xml` |
| 10 | 3.757 | `tests.architecture.test_antipatterns::test_no_blocking_io_in_async` | `junit_parallel.xml` |
| 11 | 3.514 | `tests.architecture.test_lint_terminology_script::test_lint_terminology_supports_check_without_paths` | `junit_parallel.xml` |
| 12 | 3.493 | `tests.unit.domain.test_exceptions.TestErrorClassifier::test_classify_unknown_exception` | `junit_parallel.xml` |
| 13 | 3.291 | `tests.architecture.test_di_compliance.TestDICompliance::test_factories_only_in_composition` | `junit_parallel.xml` |
| 14 | 3.192 | `tests.architecture.test_regression_metrics::test_architecture_skip_count` | `junit_parallel.xml` |
| 15 | 2.912 | `tests.test_architecture::test_no_unsafe_functions` | `junit_parallel.xml` |
| 16 | 2.87 | `tests.test_architecture::test_observability_library_isolation` | `junit_parallel.xml` |
| 17 | 2.419 | `tests.architecture.test_code_metrics.TestFunctionLength::test_functions_under_100_lines` | `junit_parallel.xml` |
| 18 | 2.415 | `tests.architecture.test_deterministic_sort_policy_coverage::test_entity_pipeline_sink_sort_policy_coverage_is_full` | `junit_parallel.xml` |
| 19 | 2.378 | `tests.architecture.test_regression_metrics::test_cross_layer_group_edges_budget` | `junit_parallel.xml` |
| 20 | 2.342 | `tests.unit.cli.test_registry_consistency.TestRegistryConfigConsistency::test_all_registered_pipelines_have_config_files` | `junit_parallel.xml` |
| 21 | 2.311 | `tests.architecture.test_code_metrics.TestGodObjectDetection::test_large_classes_have_delegation` | `junit_parallel.xml` |
| 22 | 2.191 | `tests.architecture.test_quality_burndown_priorities::test_function_length_registry_has_no_stale_entries` | `junit_parallel.xml` |
| 23 | 2.165 | `tests.architecture.test_domain_purity.TestDomainImmutability::test_no_mutable_defaults_in_frozen_dataclasses` | `junit_parallel.xml` |
| 24 | 2.146 | `tests.unit.infrastructure.validation.test_pandera_validator.TestPanderaValidatorPropertyBased::test_silver_validator_never_raises_on_arbitrary_input` | `junit_parallel.xml` |
| 25 | 2.127 | `tests.unit.infrastructure.validation.test_pandera_validator.TestPanderaValidatorPropertyBased::test_strict_mode_without_schema_always_fails` | `junit_parallel.xml` |

## Top Slow Zones

| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |
|---:|---|---:|---:|---:|
| 1 | `tests.architecture.test_regression_metrics` | 3 | 24.756 | 19.186 |
| 2 | `tests.architecture.test_antipatterns` | 2 | 19.624 | 15.867 |
| 3 | `tests.unit.infrastructure.validation.test_pandera_validator.TestPanderaValidatorPropertyBased` | 3 | 8.814 | 4.541 |
| 4 | `tests.test_architecture` | 2 | 5.782 | 2.912 |
| 5 | `tests.unit.interfaces.cli.test_cli_main_module.TestCliMainModule` | 1 | 5.741 | 5.741 |
| 6 | `tests.architecture.test_test_structural_debt` | 1 | 4.29 | 4.29 |
| 7 | `tests.architecture.test_layer_dependencies` | 1 | 4.204 | 4.204 |
| 8 | `tests.architecture.test_scripts_lifecycle_registry` | 1 | 4.108 | 4.108 |
| 9 | `tests.architecture.test_scripts_deprecation_backlog` | 1 | 4.051 | 4.051 |
| 10 | `tests.architecture.test_scripts_inventory_manifest` | 1 | 3.948 | 3.948 |

