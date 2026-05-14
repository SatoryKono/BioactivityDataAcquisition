"""Unit tests for custom DQ rule evaluators."""

from __future__ import annotations

from bioetl.domain.behavior._dq_rule_evaluators import _field_rule_violated
from bioetl.domain.config.validation import FieldValidation


def test_target_component_types_json_vocab_custom_rule_accepts_canonical_json() -> None:
    rule = FieldValidation(
        field="component_types",
        validation_type="custom",
        validator="validate_target_component_types_json_vocab",
    )

    assert (
        _field_rule_violated(
            {"component_types": '["DNA","PROTEIN"]'},
            rule,
        )
        is False
    )


def test_target_component_types_json_vocab_custom_rule_rejects_unknown_member() -> None:
    rule = FieldValidation(
        field="component_types",
        validation_type="custom",
        validator="validate_target_component_types_json_vocab",
    )

    assert (
        _field_rule_violated(
            {"component_types": '["PROTEIN","UNKNOWN_COMPONENT"]'},
            rule,
        )
        is True
    )


def test_target_component_relationships_json_vocab_custom_rule_rejects_malformed_json() -> None:
    rule = FieldValidation(
        field="component_relationships",
        validation_type="custom",
        validator="validate_target_component_relationships_json_vocab",
    )

    assert (
        _field_rule_violated(
            {"component_relationships": "not-json"},
            rule,
        )
        is True
    )
