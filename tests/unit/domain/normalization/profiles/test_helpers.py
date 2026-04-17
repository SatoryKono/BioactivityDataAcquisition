"""Tests for shared normalization profile helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_abstract,
    normalize_profile_canonical_smiles,
    normalize_profile_date,
    normalize_profile_doi,
    normalize_profile_float,
    normalize_profile_int,
    normalize_profile_isomeric_smiles,
    normalize_profile_json_string,
    normalize_profile_passthrough,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_smiles,
    normalize_profile_text,
    normalize_profile_title,
)


def test_normalize_profile_text_trims_blank_to_none() -> None:
    assert normalize_profile_text("  x  ") == "x"
    assert normalize_profile_text("   ") is None


def test_normalize_profile_json_string_canonicalizes_order() -> None:
    assert normalize_profile_json_string(' { "b": 2, "a": 1 } ') == '{"a":1,"b":2}'


def test_normalize_profile_passthrough_preserves_value() -> None:
    marker = object()
    assert normalize_profile_passthrough(marker) is marker
    assert normalize_profile_passthrough("  x  ") == "  x  "


def test_normalize_profile_title_and_abstract_clean_html_and_whitespace() -> None:
    assert normalize_profile_title("  Example <b>Title</b>  ") == "Example Title"
    assert normalize_profile_abstract(" Hello&nbsp;<i>world</i> ") == "Hello world"


def test_normalize_profile_date_canonicalizes_partial_dates() -> None:
    assert normalize_profile_date(" 2024-02 ") == "2024-02-29"


def test_normalize_profile_int_preserves_invalid_text() -> None:
    assert normalize_profile_int(" 42 ") == 42
    assert normalize_profile_int("abc") == "abc"


def test_normalize_profile_float_rounds_and_preserves_unhandled_object() -> None:
    marker = object()
    assert normalize_profile_float("1.234567890123") == pytest.approx(1.2345678901)
    assert normalize_profile_float(marker) is marker


def test_normalize_profile_identifier_helpers() -> None:
    assert normalize_profile_doi(" https://doi.org/10.1000/XYZ ") == "10.1000/xyz"
    assert normalize_profile_pmid(" PMID:12345 ") == "12345"
    assert normalize_profile_pmc_id(" pmc12345 ") == "PMC12345"


def test_normalize_profile_smiles_returns_canonical_text_or_none() -> None:
    assert normalize_profile_smiles(None, is_canonical=True) is None
    assert normalize_profile_smiles("C", is_canonical=True) == "C"


def test_normalize_profile_smiles_specializations_delegate_to_shared_seam() -> None:
    assert normalize_profile_canonical_smiles("C") == "C"
    assert normalize_profile_isomeric_smiles("C") == "C"


def test_normalize_profile_title_and_abstract_use_canonical_text_rules() -> None:
    assert normalize_profile_title("  Example   Title ") == "Example Title"
    assert normalize_profile_abstract("  Example   abstract  ") == "Example abstract"


def test_normalize_profile_date_uses_partial_date_normalization() -> None:
    assert normalize_profile_date(" 2024-01-02 ") == "2024-01-02"
