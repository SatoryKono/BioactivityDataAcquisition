"""Tests for pure join-key normalization helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.normalization.join_keys import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    get_join_key_normalization_policy,
    normalize_join_key_scalar,
    normalize_join_key_text,
    stringify_join_key_value,
)


pytestmark = pytest.mark.unit


def _iter_join_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value.get("join_keys", ()) or ())
        for child_value in value.values():
            keys.update(_iter_join_keys(child_value))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_iter_join_keys(item))
        return keys
    return set()


def test_join_keys__lowercase_for_doi__f5da2aef() -> None:
    assert (
        normalize_join_key_text(" https://doi.org/10.1000/ABC ", key="doi")
        == "10.1000/abc"
    )


def test_normalize_join_key_text_applies_publication_title_cleanup() -> None:
    raw = "  A&nbsp;<i>Mixed</i>\x07\nTitle  "

    assert normalize_join_key_text(raw, key="title") == "A Mixed Title"


def test_normalize_join_key_scalar_preserves_non_string_values() -> None:
    assert normalize_join_key_scalar(42, key="pmid") == 42


@pytest.mark.parametrize(
    ("key", "raw_value", "expected"),
    (
        ("doi", " 10.1000/ABC ", "10.1000/abc"),
        ("inchi_key", " bsynrymutxbxsq-uhfffaoysa-n ", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"),
        ("pmid", " PMID:12345 ", "12345"),
        ("pmc_id", " PMC123 ", "pmc123"),
        ("target_id", " chembl0203 ", "CHEMBL203"),
        ("uniprot_accession", " p12345 ", "P12345"),
        ("title", "  Mixed\t Case\nTitle  ", "Mixed Case Title"),
        ("canonical_smiles", " C[C@H](O)C ", "C[C@H](O)C"),
    ),
)
def test_normalize_join_key_text_covers_supported_mutating_families(
    key: str,
    raw_value: str,
    expected: str,
) -> None:
    assert normalize_join_key_text(raw_value, key=key) == expected


def test_stringify_join_key_value_normalizes_float_ints_and_strings() -> None:
    assert stringify_join_key_value(42.0, key="pmid") == "42"
    assert stringify_join_key_value(" PMC123 ", key="pmc_id") == "pmc123"


def test_invalid_identifier_family_collapses_to_empty_join_key() -> None:
    assert normalize_join_key_text("PMC1234567", key="pmid") is None
    assert stringify_join_key_value("PMC1234567", key="pmid") == ""


def test_stringify_join_key_value_handles_none_empty_and_real_float_stably() -> None:
    assert stringify_join_key_value(None, key="doi") == ""
    assert stringify_join_key_value("", key="doi") == ""
    assert stringify_join_key_value(42.5, key="pmid") == "42.5"


def test_compound_join_key_components_normalize_to_equivalent_values() -> None:
    tuple_a = (
        stringify_join_key_value(" 10.1000/ABC ", key="doi"),
        stringify_join_key_value("  Mixed\t Case\nTitle  ", key="title"),
    )
    tuple_b = (
        stringify_join_key_value("10.1000/abc", key="doi"),
        stringify_join_key_value("Mixed Case Title", key="title"),
    )

    assert tuple_a == tuple_b == ("10.1000/abc", "Mixed Case Title")


def test_join_key_policy_registry_exposes_known_keys() -> None:
    policy = get_join_key_normalization_policy("doi")

    assert policy is not None
    assert JOIN_KEY_NORMALIZATION_POLICIES["doi"] is policy
    assert policy.trim is True
    assert policy.lowercase is True


def test_configured_composite_join_keys_have_explicit_normalization_policies() -> None:
    configured_keys: set[str] = set()
    for config_path in Path("configs/composites").glob("*.yaml"):
        configured_keys.update(_iter_join_keys(yaml.safe_load(config_path.read_text())))

    assert configured_keys
    assert configured_keys <= set(JOIN_KEY_NORMALIZATION_POLICIES)
