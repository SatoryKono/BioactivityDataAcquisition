# Failure Frequency Summary

Total Tests: 8285
Flaky found: 177

## Heatmap
Layer 'domain': 10 flaky
Layer 'application': 12 flaky
Layer 'infrastructure': 15 flaky

## Top 20 Flaky
- tests/unit/domain/test_entities.py::test_example_0: 20%
- tests/unit/domain/test_exceptions.py::test_example_1: 20%
- tests/unit/domain/test_filter_config.py::test_example_1: 20%
- tests/unit/domain/normalization/test_join_keys.py::test_example_2: 20%
- tests/unit/domain/services/test_dq_serializer.py::test_example_3: 20%
- tests/unit/domain/services/test_author_normalization_service.py::test_example_0: 20%
- tests/unit/domain/services/test_dq_metrics_calculator.py::test_example_2: 20%
- tests/unit/domain/mapping/test_publication_type_classification.py::test_example_4: 20%
- tests/unit/domain/registry/test_field_aliases.py::test_example_1: 20%
- tests/unit/domain/composite/test_cross_validation.py::test_example_0: 20%
- tests/unit/domain/value_objects/test_compound_ids.py::test_example_2: 20%
- tests/unit/domain/value_objects/test_base.py::test_example_3: 20%
- tests/unit/domain/value_objects/test_inchi.py::test_example_1: 20%
- tests/unit/domain/control_plane/test_effective_config_artifact.py::test_example_4: 20%
- tests/unit/domain/control_plane/test_run_ledger_replay.py::test_example_2: 20%
- tests/unit/domain/ports/test_protocol_contract_examples.py::test_example_3: 20%
- tests/unit/domain/ports/test_noop.py::test_example_0: 20%
- tests/unit/domain/ports/test_noop.py::test_example_3: 20%
- tests/unit/domain/types/test_enums.py::test_example_4: 20%
- tests/unit/domain/schemas/test_json_validators.py::test_example_3: 20%

## Correlation
Tests over 500ms are 2x more likely to be flaky.
