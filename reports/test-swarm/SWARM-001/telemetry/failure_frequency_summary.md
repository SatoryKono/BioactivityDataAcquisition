# Failure Frequency Summary

Total Tests: 24553
Flaky found: 463

## Heatmap
Layer 'domain': 10 flaky
Layer 'application': 12 flaky
Layer 'infrastructure': 15 flaky

## Top 20 Flaky
- tests/unit/domain/aggregates/test_quarantine_entry.py::test_generated_31: 20%
- tests/unit/domain/composite/test_composite_config_edge_cases.py::test_generated_6: 20%
- tests/unit/domain/composite/test_cross_validation.py::test_generated_6: 20%
- tests/unit/domain/composite/test_data_schema_config.py::test_generated_1: 20%
- tests/unit/domain/composite/test_field_groups.py::test_generated_1: 20%
- tests/unit/domain/composite/test_state.py::test_generated_51: 20%
- tests/unit/domain/config/test_base_provider.py::test_generated_5: 20%
- tests/unit/domain/configs/test_dq_config_extended.py::test_generated_8: 20%
- tests/unit/domain/control_plane/test_contract_registry.py::test_generated_11: 20%
- tests/unit/domain/control_plane/test_effective_config_artifact.py::test_generated_19: 20%
- tests/unit/domain/entities/test_chembl_entities.py::test_generated_22: 20%
- tests/unit/domain/entities/test_publication_entities.py::test_generated_18: 20%
- tests/unit/domain/entities/test_uniprot_entities.py::test_generated_3: 20%
- tests/unit/domain/filtering/test_column_filter.py::test_generated_8: 20%
- tests/unit/domain/filtering/test_gold_config.py::test_generated_7: 20%
- tests/unit/domain/mapping/test_organism_classification.py::test_generated_23: 20%
- tests/unit/domain/mapping/test_publication_type_mapping.py::test_generated_23: 20%
- tests/unit/domain/mapping/test_publication_type_mapping.py::test_generated_45: 20%
- tests/unit/domain/normalization/profiles/test_additional_profiles.py::test_generated_46: 20%
- tests/unit/domain/normalization/profiles/test_chembl_pseudo_null_policy.py::test_generated_6: 20%

## Correlation
Tests over 500ms are 2x more likely to be flaky.
