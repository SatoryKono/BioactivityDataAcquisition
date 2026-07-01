"""Unit tests for custom DQ rule evaluators."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.domain.behavior._dq_rule_evaluators import _field_rule_violated
from bioetl.domain.behavior._dq_rule_evaluators import (
    _conditional_matches,
    _cross_rule_violated,
)
from bioetl.domain.behavior._dq_condition_matchers import _condition_options
from bioetl.domain.behavior._dq_condition_matchers import _in_condition_matches
from bioetl.domain.behavior._dq_condition_matchers import _not_in_condition_matches
from bioetl.domain.behavior._dq_value_coercion import _coerce_list_like
from bioetl.domain.behavior._dq_value_coercion import _coerce_numeric_value
from bioetl.domain.behavior._dq_rule_evaluators_vocab import (
    _coerce_string_list_like,
    _coerce_target_json_list,
    _is_invalid_xref_item,
    _publication_taxonomy_rule_violated,
    _publication_taxonomy_vocabulary,
    _resolve_custom_validation_strategy,
    _target_json_vocabulary_rule_violated,
    _target_xref_json_vocabulary_rule_violated,
)
from bioetl.domain.config.validation import CrossFieldValidation
from bioetl.domain.config.validation import FieldValidation


pytestmark = pytest.mark.unit


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


def test_target_cross_references_json_vocab_custom_rule_rejects_unknown_source() -> (
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
                    '{"xref_id":"XYZ1","xref_src_db":"UnknownDB"}]'
                )
            },
            rule,
        )
        is True
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


def test_target_organism_custom_rule_accepts_supported_chembl_target_organisms() -> (
    None
):
    rule = FieldValidation(
        field="organism",
        validation_type="custom",
        validator="validate_target_organism_supported_name",
    )

    supported_cases = (
        {"organism": "Ascaris suum", "taxonomy_id": 6253},
        {"organism": "Saccharomyces cerevisiae S288c", "taxonomy_id": 559292},
        {"organism": "Penicillium chrysogenum", "taxonomy_id": 5076},
        {"organism": "Caenorhabditis elegans", "taxonomy_id": 6239},
    )

    for record in supported_cases:
        assert _field_rule_violated(record, rule) is False


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


def test_target_organism_custom_rule_keeps_binomial_fallback_without_taxonomy_id() -> (
    None
):
    rule = FieldValidation(
        field="organism",
        validation_type="custom",
        validator="validate_target_organism_supported_name",
    )

    assert (
        _field_rule_violated(
            {"organism": "Unknown blob"},
            rule,
        )
        is False
    )


def test_field_rule_dispatch_covers_required_null_range_pattern_and_enum_rules() -> None:
    assert _field_rule_violated(
        {},
        FieldValidation(field="pmid", validation_type="required"),
    )
    assert _field_rule_violated(
        {"pmid": None},
        FieldValidation(field="pmid", validation_type="not_null"),
    )
    assert not _field_rule_violated(
        {"year": 2024},
        FieldValidation(
            field="year",
            validation_type="range",
            min_value=1900,
            max_value=2100,
        ),
    )
    assert _field_rule_violated(
        {"year": "not-numeric"},
        FieldValidation(field="year", validation_type="range"),
    )
    assert not _field_rule_violated(
        {"doi": "10.1000/example"},
        FieldValidation(field="doi", validation_type="pattern", pattern=r"^10\."),
    )
    assert _field_rule_violated(
        {"doi": "bad"},
        FieldValidation(field="doi", validation_type="pattern", pattern=r"^10\."),
    )
    assert not _field_rule_violated(
        {"source": "pubmed"},
        FieldValidation(
            field="source",
            validation_type="enum",
            allowed=("pubmed", "crossref"),
        ),
    )
    assert _field_rule_violated(
        {"source": "unknown"},
        FieldValidation(
            field="source",
            validation_type="enum",
            allowed=("pubmed", "crossref"),
        ),
    )


def test_field_rule_dispatch_covers_max_length_list_custom_and_unknown_rules() -> None:
    assert not _field_rule_violated(
        {"title": "short"},
        FieldValidation(field="title", validation_type="max_length", max_length=10),
    )
    assert _field_rule_violated(
        {"title": "too long"},
        FieldValidation(field="title", validation_type="max_length", max_length=3),
    )
    assert not _field_rule_violated(
        {"authors": ["A"]},
        FieldValidation(field="authors", validation_type="not_empty_list"),
    )
    assert _field_rule_violated(
        {"authors": []},
        FieldValidation(field="authors", validation_type="not_empty_list"),
    )
    assert not _field_rule_violated(
        {"smiles": "CCO"},
        FieldValidation(
            field="smiles",
            validation_type="custom",
            validator="smiles_validator",
        ),
    )
    assert _field_rule_violated(
        {"smiles": "invalid smiles"},
        FieldValidation(
            field="smiles",
            validation_type="custom",
            validator="smiles_validator",
        ),
    )
    assert not _field_rule_violated(
        {"field": "value"},
        FieldValidation(field="field", validation_type="required"),
    )


def test_field_rule_dispatch_covers_malformed_rule_inputs_and_unknown_dispatcher() -> None:
    unknown_rule = SimpleNamespace(field="field", validation_type="unknown")
    assert not _field_rule_violated({"field": "value"}, unknown_rule)  # type: ignore[arg-type]

    assert _field_rule_violated(
        {"doi": "10.1000/example"},
        FieldValidation(field="doi", validation_type="pattern", pattern=None),
    )
    assert _field_rule_violated(
        {"doi": 10},
        FieldValidation(field="doi", validation_type="pattern", pattern=r"^10\."),
    )
    assert _field_rule_violated(
        {"title": "short"},
        FieldValidation(field="title", validation_type="max_length", max_length=None),
    )
    assert _field_rule_violated(
        {"title": 123},
        FieldValidation(field="title", validation_type="max_length", max_length=5),
    )
    assert _field_rule_violated(
        {"authors": object()},
        FieldValidation(field="authors", validation_type="not_empty_list"),
    )
    assert not _field_rule_violated(
        {"field": "value"},
        FieldValidation(field="field", validation_type="custom", validator="unknown"),
    )
    assert _field_rule_violated(
        {"protein_class_id": "PC1", "parent_id": "PC1"},
        FieldValidation(
            field="protein_class_id",
            validation_type="custom",
            validator="validate_hierarchy_no_self_reference",
        ),
    )


def test_field_rule_dispatch_ignores_optional_missing_values() -> None:
    assert not _field_rule_violated(
        {},
        FieldValidation(field="optional", validation_type="range"),
    )
    assert not _field_rule_violated(
        {"optional": None},
        FieldValidation(field="optional", validation_type="pattern", pattern=r".+"),
    )
    assert not _field_rule_violated(
        {"optional": None},
        FieldValidation(field="optional", validation_type="enum", allowed=("x",)),
    )
    assert not _field_rule_violated(
        {"optional": None},
        FieldValidation(field="optional", validation_type="custom", validator="unknown"),
    )


def test_cross_rule_dispatch_covers_standard_conditions_and_unknown_condition() -> None:
    assert _cross_rule_violated(
        {"a": 1},
        CrossFieldValidation(name="all", fields=("a", "b"), condition="all_present"),
    )
    assert _cross_rule_violated(
        {"a": None, "b": None},
        CrossFieldValidation(name="any", fields=("a", "b"), condition="any_present"),
    )
    assert _cross_rule_violated(
        {"a": 1, "b": 2},
        CrossFieldValidation(
            name="exclusive",
            fields=("a", "b"),
            condition="mutually_exclusive",
        ),
    )
    assert _cross_rule_violated(
        {"trigger": "yes"},
        CrossFieldValidation(
            name="conditional",
            fields=("trigger", "required"),
            condition="conditional_required",
            trigger_field="trigger",
            required_field="required",
        ),
    )
    assert not _cross_rule_violated(
        {"trigger": None},
        CrossFieldValidation(
            name="conditional",
            fields=("trigger", "required"),
            condition="conditional_required",
            trigger_field="trigger",
            required_field="required",
        ),
    )
    assert _cross_rule_violated(
        {"protein_class_id": "PC1", "parent_id": "PC1"},
        CrossFieldValidation(
            name="custom",
            fields=("protein_class_id", "parent_id"),
            condition="custom",
            validator="validate_hierarchy_no_self_reference",
        ),
    )
    assert not _cross_rule_violated(
        {"a": 1},
        CrossFieldValidation(name="unknown", fields=("a",), condition="custom"),
    )
    unknown_rule = SimpleNamespace(fields=("a",), condition="unknown")
    assert not _cross_rule_violated({"a": 1}, unknown_rule)  # type: ignore[arg-type]


def test_cross_rule_equality_passes_with_zero_or_one_present_value() -> None:
    rule = CrossFieldValidation(
        name="alias_eq",
        fields=("doi", "publication_doi"),
        condition="equality",
    )

    assert _cross_rule_violated({}, rule) is False
    assert _cross_rule_violated({"doi": "10.1000/xyz"}, rule) is False
    assert _cross_rule_violated({"publication_doi": "10.1000/xyz"}, rule) is False


def test_cross_rule_equality_detects_mismatched_present_values() -> None:
    rule = CrossFieldValidation(
        name="alias_eq",
        fields=("doi", "publication_doi"),
        condition="equality",
    )

    assert (
        _cross_rule_violated(
            {"doi": "10.1000/xyz", "publication_doi": "10.1000/xyz"},
            rule,
        )
        is False
    )
    assert (
        _cross_rule_violated(
            {"doi": "10.1000/xyz", "publication_doi": "10.1000/abc"},
            rule,
        )
        is True
    )


class _ConditionalRule:
    condition_field = "kind"
    condition_operator = "eq"
    condition_value = "target"


class _UnknownConditionalRule:
    condition_field = "kind"
    condition_operator = "unknown"
    condition_value = "target"


def test_conditional_matches_uses_registered_matchers_and_unknown_operator_is_false() -> None:
    assert _conditional_matches({"kind": "target"}, _ConditionalRule()) is True  # type: ignore[arg-type]
    assert _conditional_matches({"kind": "other"}, _ConditionalRule()) is False  # type: ignore[arg-type]
    assert _conditional_matches({"kind": "target"}, _UnknownConditionalRule()) is False  # type: ignore[arg-type]


def test_condition_options_and_membership_matchers_are_tuple_stable() -> None:
    assert _condition_options("target") == ("target",)
    assert _condition_options(("target", "decoy")) == ("target", "decoy")
    assert _in_condition_matches("target", ("target", "decoy")) is True
    assert _in_condition_matches("missing", "target") is False
    assert _not_in_condition_matches("missing", ("target", "decoy")) is True
    assert _not_in_condition_matches("target", "target") is False


def test_value_coercion_rejects_bool_numeric_and_decodes_json_lists() -> None:
    assert _coerce_numeric_value(True) is None
    assert _coerce_numeric_value("1.25") == 1.25
    assert _coerce_numeric_value("not-numeric") is None
    assert _coerce_list_like(("a", "b")) == ["a", "b"]
    assert sorted(_coerce_list_like({"b", "a"}) or []) == ["a", "b"]
    assert _coerce_list_like('["a", 1]') == ["a", 1]
    assert _coerce_list_like("not-json") is None


def test_vocabulary_strategy_resolution_and_target_json_coercion() -> None:
    strategy = _resolve_custom_validation_strategy(
        "validate_target_component_types_json_vocab"
    )
    assert strategy is not None
    assert strategy('["PROTEIN"]', "validate_target_component_types_json_vocab") is False
    assert strategy('["UNKNOWN"]', "validate_target_component_types_json_vocab") is True
    assert _resolve_custom_validation_strategy("missing") is None

    assert _coerce_string_list_like("") == []
    assert _coerce_string_list_like("{}") is None
    assert _coerce_string_list_like("[not-json]") is None
    assert _coerce_target_json_list(["PROTEIN"]) == ["PROTEIN"]
    assert _coerce_target_json_list({"bad": "shape"}) is None
    assert _target_json_vocabulary_rule_violated(
        ["PROTEIN", 123],
        allowed_values=frozenset({"PROTEIN"}),
    )


def test_xref_and_publication_taxonomy_vocabulary_strategies() -> None:
    xref_strategy = _resolve_custom_validation_strategy(
        "validate_target_xref_src_db_json_vocab"
    )
    assert xref_strategy is not None
    assert (
        xref_strategy(
            '[{"xref_src_db":"UniProt"}]',
            "validate_target_xref_src_db_json_vocab",
        )
        is False
    )
    assert (
        xref_strategy(
            '[{"xref_src_db":"UnknownDB"}]',
            "validate_target_xref_src_db_json_vocab",
        )
        is True
    )
    assert _target_xref_json_vocabulary_rule_violated(
        ["bad"],
        allowed_values=frozenset({"UniProt"}),
    )
    assert _is_invalid_xref_item({"xref_src_db": 1}, frozenset({"UniProt"}))

    taxonomy = _publication_taxonomy_vocabulary(
        "validate_publication_type_unified_taxonomy"
    )
    assert taxonomy is not None
    taxonomy_strategy = _resolve_custom_validation_strategy(
        "validate_publication_type_unified_taxonomy"
    )
    assert taxonomy_strategy is not None
    assert (
        taxonomy_strategy("not-in-taxonomy", "validate_publication_type_unified_taxonomy")
        is True
    )
    assert not _publication_taxonomy_rule_violated(
        "research-article",
        allowed_values=frozenset({"research-article"}),
    )
    assert _publication_taxonomy_rule_violated(
        123,
        allowed_values=frozenset({"research-article"}),
    )
