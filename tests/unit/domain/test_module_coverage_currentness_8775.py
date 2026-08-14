"""Domain coverage regression vectors for #8775."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior import schema_metadata_extractor
from bioetl.domain.behavior._preflight_governance_types import (
    GovernancePolicy,
    PreflightGovernanceConfig,
)
from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_helpers import (
    _convert_to_aggregation_config,
    _convert_to_cross_validation_config,
)
from bioetl.domain.behavior.dq_serializer import DQReportSerializer, to_dict
from bioetl.domain.behavior.merged_metadata_explainability import (
    _deterministic_record_id,
    _json_fallback,
)
from bioetl.domain.behavior.normalization_config import NormalizationConfig
from bioetl.domain.composite.config_composite_section_decoders import (
    _enricher_field_pairings,
    _field_comparison_specs,
)
from bioetl.domain.config.dq import DQReportConfig
from bioetl.domain.config.validation_rules import FieldValidation
from bioetl.domain.types.validation_severity import ValidationSeverity
from bioetl.domain.value_objects._run_context_create_support import (
    _coerce_transform_step_sequence,
    _resolve_create_input_value,
)


pytestmark = pytest.mark.unit


def test_preflight_config_hash_includes_immutable_overrides() -> None:
    config = PreflightGovernanceConfig(
        policy=GovernancePolicy.CI_STRICT,
        issue_code_overrides={"DQ-1": ValidationSeverity.WARNING},
    )

    assert isinstance(hash(config), int)


def test_aggregation_schema_helpers_cover_descriptor_shapes() -> None:
    assert AggregationValidator._field_names_from_list([{"name": "entity_id"}]) == {
        "entity_id"
    }
    assert AggregationValidator._collect_fallback_fields(
        {"columns": [{"name": "score"}], "field_names": ["entity_id"]}
    ) == {"score", "entity_id"}
    assert AggregationValidator._build_group_key({"group": None}, ["group"]) == (
        ("present", "NoneType", "null"),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"group_by": [1]},
        {"aggregations": {1: "sum"}},
        {"aggregations": {"x": 1}},
        {"source_field": 1},
        {"provenance_tracking": "yes"},
    ],
)
def test_aggregation_config_rejects_typed_shape_errors(
    payload: dict[str, object],
) -> None:
    with pytest.raises(TypeError):
        _convert_to_aggregation_config(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"pairs": [1]},
        {"rules": {1: "equals"}},
        {"rules": {"x": 1}},
        {"strict_mode": "yes"},
        {"coverage_threshold": "high"},
        {"consistency_threshold": 2.0},
    ],
)
def test_cross_validation_config_rejects_typed_shape_errors(
    payload: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _convert_to_cross_validation_config(payload)


def test_dq_serializer_handles_binary_and_nested_empty_collections() -> None:
    serializer = DQReportSerializer()

    assert to_dict({"payload": b"\x0f"})["payload"] == "0f"
    rendered = serializer._dict_to_yaml(
        {
            "nested": {"value": 1},
            "items": [{}, [], [1]],
        }
    )

    assert "nested:" in rendered
    assert "- {}" in rendered
    assert "- []" in rendered
    assert serializer._quote_yaml_string("a: b")


def test_explainability_ids_handle_mixed_keys_and_fallback_scalars() -> None:
    first = _deterministic_record_id({1: "one", "2": "two"})  # type: ignore[dict-item]

    assert len(first) == 64
    assert _json_fallback(b"\x0f") == "0f"
    assert "object" in str(_json_fallback(object()))


def test_normalization_rejects_negative_high_potency_threshold() -> None:
    with pytest.raises(ValueError, match="high_potency_threshold cannot be negative"):
        NormalizationConfig(high_potency_threshold=-1)


def test_schema_metadata_exception_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema_metadata_extractor.inspect,
        "getmodule",
        lambda _value: (_ for _ in ()).throw(TypeError("bad module")),
    )
    assert schema_metadata_extractor._extract_contract_path(object()) is None

    monkeypatch.setattr(
        schema_metadata_extractor,
        "_safe_to_schema",
        lambda _value: (_ for _ in ()).throw(RuntimeError("not pandera")),
    )
    with pytest.raises(RuntimeError, match="not pandera"):
        schema_metadata_extractor._extract_schema_columns(object())

    from pandera.errors import SchemaDefinitionError

    assert schema_metadata_extractor._is_pandera_schema_error(
        SchemaDefinitionError("invalid schema")
    )


def test_schema_metadata_handles_missing_schema_surface() -> None:
    assert schema_metadata_extractor._extract_schema_columns(object()) == []
    assert schema_metadata_extractor._safe_to_schema(object()) is not None


def test_composite_optional_sections_normalize_to_empty_tuples() -> None:
    assert _field_comparison_specs(None, path="fields") == ()
    assert _enricher_field_pairings(None) == ()


def test_dq_and_validation_rule_invalid_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="sample_size"):
        DQReportConfig(sample_size=-1)
    assert (
        FieldValidation(field="x", validation_type="range", max_value=1).max_value == 1
    )
    with pytest.raises(ValueError, match="min_value must be"):
        FieldValidation(field="x", validation_type="range", min_value=2, max_value=1)
    with pytest.raises(ValueError, match="validator name"):
        FieldValidation(field="x", validation_type="custom")


def test_run_context_create_coercion_rejects_invalid_vectors() -> None:
    with pytest.raises(TypeError, match="sequence of strings"):
        _coerce_transform_step_sequence([1])
    with pytest.raises(TypeError, match="sequence of strings"):
        _coerce_transform_step_sequence(object())
    with pytest.raises(TypeError, match="missing required argument"):
        _resolve_create_input_value(
            field_name="provider",
            inputs=None,
            overrides={},
        )
