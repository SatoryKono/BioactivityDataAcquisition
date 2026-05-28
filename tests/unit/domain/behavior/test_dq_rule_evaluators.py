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


def test_target_component_relationships_json_vocab_custom_rule_rejects_malformed_json() -> (
    None
):
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


def test_target_cross_references_json_vocab_custom_rule_accepts_governed_sources() -> (
    None
):
    rule = FieldValidation(
        field="cross_references",
        validation_type="custom",
        validator="validate_target_xref_src_db_json_vocab",
    )

    assert (
        _field_rule_violated(
            {
                "cross_references": (
                    '[{"xref_id":"P12345","xref_src_db":"UniProt"},'
                    '{"xref_id":"IPR000001","xref_src_db":"InterPro"}]'
                )
            },
            rule,
        )
        is False
    )


def test_target_cross_references_json_vocab_custom_rule_accepts_cgd_source() -> None:
    rule = FieldValidation(
        field="cross_references",
        validation_type="custom",
        validator="validate_target_xref_src_db_json_vocab",
    )

    assert (
        _field_rule_violated(
            {"cross_references": ('[{"xref_id":"CAL0000189182","xref_src_db":"CGD"}]')},
            rule,
        )
        is False
    )


def test_target_component_xrefs_json_vocab_custom_rule_rejects_unknown_source() -> None:
    rule = FieldValidation(
        field="target_component_xrefs",
        validation_type="custom",
        validator="validate_target_component_xref_src_db_json_vocab",
    )

    assert (
        _field_rule_violated(
            {
                "target_component_xrefs": (
                    '[{"xref_id":"P12345","xref_src_db":"UniProt"},'
                    '{"xref_id":"XYZ1","xref_src_db":"UnknownDB"}]'
                )
            },
            rule,
        )
        is True
    )


def test_target_organism_custom_rule_accepts_classifiable_non_binomial_names() -> None:
    rule = FieldValidation(
        field="organism",
        validation_type="custom",
        validator="validate_target_organism_supported_name",
    )

    assert (
        _field_rule_violated(
            {"organism": "Bacteria", "taxonomy_id": 2},
            rule,
        )
        is False
    )
    assert (
        _field_rule_violated(
            {
                "organism": "Influenza A virus (strain A/Aichi/2/1968 H3N2)",
                "taxonomy_id": 387139,
            },
            rule,
        )
        is False
    )
    assert (
        _field_rule_violated(
            {"organism": "Trichophyton", "taxonomy_id": 5550},
            rule,
        )
        is False
    )


def test_target_organism_custom_rule_rejects_unclassifiable_non_binomial_name() -> None:
    rule = FieldValidation(
        field="organism",
        validation_type="custom",
        validator="validate_target_organism_supported_name",
    )

    assert (
        _field_rule_violated(
            {"organism": "Unknown blob", "taxonomy_id": 999999},
            rule,
        )
        is True
    )
