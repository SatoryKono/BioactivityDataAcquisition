"""Unit tests for shared application normalization fallback helpers."""

from __future__ import annotations

import pytest

from bioetl.application.core.normalization_fallbacks import (
    UNHANDLED_FALLBACK_NORMALIZATION,
    canonicalize_json_like_string,
    is_date_field,
    is_doi_field,
    is_json_like_string,
    is_pmid_field,
    is_smiles_field,
    normalize_named_text_field,
    normalize_special_fallback_field,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy


pytestmark = pytest.mark.unit

def test_field_classifiers_cover_expected_fallback_cases() -> None:
    rules = NormalizationRulesPolicy()
    assert is_doi_field("publication_doi", rule_set=rules) is True
    assert is_pmid_field("publication_pmid", rule_set=rules) is True
    assert is_date_field("publication_date", rule_set=rules) is True
    assert is_date_field("created_ts", rule_set=rules) is False
    assert is_smiles_field("canonical_smiles") is True


def test_json_like_string_detection_and_canonicalization() -> None:
    assert is_json_like_string(' {"b":2,"a":1} ') is True
    assert is_json_like_string("plain text") is False
    assert canonicalize_json_like_string(' {"b":2,"a":1} ') == '{"a":1,"b":2}'
    assert canonicalize_json_like_string("{not json}") == "{not json}"


def test_named_text_fallback_normalizers_use_rule_buckets() -> None:
    rules = NormalizationRulesPolicy()
    assert (
        normalize_named_text_field("title", "  Example <b>Title</b>  ", rule_set=rules)
        == "Example Title"
    )
    assert (
        normalize_named_text_field("abstract", "  Example   abstract  ", rule_set=rules)
        == "Example abstract"
    )
    assert normalize_named_text_field("oa_status", " GOLD ", rule_set=rules) == "gold"
    assert normalize_named_text_field("other", " value ", rule_set=rules) is None


def test_special_fallback_normalizers_delegate_to_canonical_helpers() -> None:
    rules = NormalizationRulesPolicy()
    assert (
        normalize_special_fallback_field(
            "publication_doi",
            " https://doi.org/10.1000/ABC ",
            rule_set=rules,
        )
        == "10.1000/abc"
    )
    assert (
        normalize_special_fallback_field(
            "publication_pmid", " PMID:12345 ", rule_set=rules
        )
        == "12345"
    )
    assert (
        normalize_special_fallback_field("publication_date", "2024-02", rule_set=rules)
        == "2024-02-29"
    )
    assert (
        normalize_special_fallback_field("canonical_smiles", "C", rule_set=rules) == "C"
    )
    assert (
        normalize_special_fallback_field("other", "value", rule_set=rules)
        is UNHANDLED_FALLBACK_NORMALIZATION
    )
