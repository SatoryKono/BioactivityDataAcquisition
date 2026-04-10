"""Tests for pure join-key normalization helpers."""

from __future__ import annotations

from bioetl.domain.normalization.join_keys import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    get_join_key_normalization_policy,
    normalize_join_key_scalar,
    normalize_join_key_text,
    stringify_join_key_value,
)


def test_normalize_join_key_text_applies_trim_and_lowercase_for_doi() -> None:
    assert normalize_join_key_text(" 10.1000/ABC ", key="doi") == "10.1000/abc"


def test_normalize_join_key_scalar_preserves_non_string_values() -> None:
    assert normalize_join_key_scalar(42, key="pmid") == 42


def test_stringify_join_key_value_normalizes_float_ints_and_strings() -> None:
    assert stringify_join_key_value(42.0, key="pmid") == "42"
    assert stringify_join_key_value(" PMC123 ", key="pmc_id") == "pmc123"


def test_join_key_policy_registry_exposes_known_keys() -> None:
    policy = get_join_key_normalization_policy("doi")

    assert policy is not None
    assert JOIN_KEY_NORMALIZATION_POLICIES["doi"] is policy
    assert policy.trim is True
    assert policy.lowercase is True
