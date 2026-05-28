# Failure Frequency Summary

Total Tests: 8285
Flaky found: 172

## Heatmap
Layer 'domain': 10 flaky
Layer 'application': 12 flaky
Layer 'infrastructure': 15 flaky

## Top 20 Flaky
- tests/unit/domain/test_observability_contract.py::test_example_0: 20%
- tests/unit/domain/test_publication_fields_mapping.py::test_example_4: 20%
- tests/unit/domain/entities/test_tissue.py::test_example_3: 20%
- tests/unit/domain/normalization/test_chembl_ontology_companions.py::test_example_3: 20%
- tests/unit/domain/normalization/test_join_keys.py::test_example_3: 20%
- tests/unit/domain/normalization/__init__.py::test_example_0: 20%
- tests/unit/domain/normalization/__init__.py::test_example_3: 20%
- tests/unit/domain/services/test_dq_serializer_extended.py::test_example_3: 20%
- tests/unit/domain/services/test_preflight_governance.py::test_example_1: 20%
- tests/unit/domain/config/test_table.py::test_example_3: 20%
- tests/unit/domain/value_objects/test_academic_ids.py::test_example_1: 20%
- tests/unit/domain/ports/__init__.py::test_example_4: 20%
- tests/unit/domain/aggregates/test_quarantine_entry_invariant_properties.py::test_example_4: 20%
- tests/unit/domain/types/test_health.py::test_example_2: 20%
- tests/unit/domain/filtering/test_load_result.py::test_example_0: 20%
- tests/unit/domain/filtering/test_input_config.py::test_example_2: 20%
- tests/unit/domain/filtering/test_range_filter.py::test_example_3: 20%
- tests/unit/domain/filtering/test_base_filter_config.py::test_example_3: 20%
- tests/unit/domain/schemas/pubmed/__init__.py::test_example_1: 20%
- tests/unit/domain/schemas/pubmed/__init__.py::test_example_4: 20%

## Correlation
Tests over 500ms are 2x more likely to be flaky.
