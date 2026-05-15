# Failure Frequency Analysis

**Task**: SWARM-001
**Generated**: 2026-05-15 10:46

## Top 20 Flaky Tests
| Test ID | Frequency | Flaky Index | Alert Level |
|---------|-----------|-------------|-------------|
| tests/unit/domain/test_normalization.py::TestParseAuthorsToList::test_parse_authors_json_unicode | 0.2 | 0.2 | critical |
| tests/unit/domain/entities/test_uniprot_entities.py::TestIDMappingResult::test_valid_mapping_statuses[not_found] | 0.2 | 0.2 | critical |
| tests/unit/domain/composite/test_cross_validation.py::TestComparisonMethod::test_is_str_enum | 0.2 | 0.2 | critical |
| tests/unit/domain/value_objects/test_dq_metrics.py::TestSchemaDriftInfo::test_default_values | 0.2 | 0.2 | critical |
| tests/unit/domain/normalization/profiles/test_chembl_pseudo_null_policy.py::test_chembl_pseudo_null_fields_collapse_to_none[molecule-atc_classifications-None] | 0.2 | 0.2 | critical |
| tests/unit/application/core/test_base_transformer.py::TestTemplateMethodPattern::test_transform_applies_structural_policy_before_silver_filter | 0.2 | 0.2 | critical |
| tests/unit/application/pipelines/pubmed/test_pubmed_transformer.py::TestPubMedTransformerIdentifierNormalization::test_empty_pii_normalized_to_none | 0.2 | 0.2 | critical |
| tests/unit/application/composite/test_merger.py::TestDeduplicateEnricher::test_no_duplicates_returns_unchanged | 0.2 | 0.2 | critical |
| tests/unit/application/services/test_medallion_lifecycle.py::TestMedallionLifecycleServiceVacuum::test_vacuum_dry_run | 0.2 | 0.2 | critical |
| tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_bao_and_uo_identifiers | 0.2 | 0.2 | critical |
| tests/unit/infrastructure/schemas/test_base_schemas.py::TestBaseInputFilterConfig::test_enabled_requires_column_config | 0.2 | 0.2 | critical |
| tests/unit/infrastructure/storage/test_bronze_writer_metrics_mixin.py::TestBronzeWriterMetricsMixin::test_emit_bronze_write_metrics_observes_histogram | 0.2 | 0.2 | critical |
| tests/unit/infrastructure/quality/test_decomposition_validation.py::TestValidateProgramDoneCriteriaSection::test_valid_criteria | 0.2 | 0.2 | critical |
| tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies.py::TestPubChemFetchStrategiesInit::test_init_preserves_injected_collaborators | 0.2 | 0.2 | critical |
| tests/unit/infrastructure/observability/test_debug_adapters_boost.py::TestInteractiveDebugAdapter::test_on_breakpoint_without_message | 0.2 | 0.2 | critical |
| tests/unit/composition/test_generic_factory.py::TestGenericPipelineFactory::test_build_services | 0.2 | 0.2 | critical |
| tests/unit/interfaces/cli/commands/test_health.py::TestHealthServerCommand::test_start_health_observability_skips_when_disabled | 0.2 | 0.2 | critical |
| tests/unit/composition/factories/pipeline/test_registry_consistency.py::TestRegistryNameUniqueness::test_registry_has_unique_names | 0.2 | 0.2 | critical |
| tests/unit/composition/test_workflow_services.py::test_get_workflow_execution_service_injects_real_manifest_clock | 0.2 | 0.2 | critical |
| tests/unit/interfaces/cli/test_cli_commands.py::test_run_command_with_cli_policy_wires_registry_and_cli_seams | 0.2 | 0.2 | critical |

## Heatmap
- domain: ⚠️
- application: ⚠️
- infrastructure: ⚠️
- composition: ⚠️

## Correlation
No clear correlation between duration and flakiness detected.
