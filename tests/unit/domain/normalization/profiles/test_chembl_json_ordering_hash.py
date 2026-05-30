"""Unit tests for reviewed ChEMBL JSON ordering hash semantics."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import resolve_normalization_profile
from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY_HASH,
    CHEMBL_JSON_ORDERING_POLICY_VERSION,
    chembl_order_sensitive_json_fields,
    chembl_set_like_json_fields,
)


def test_chembl_json_ordering_policy_exposes_versioned_hash() -> None:
    assert CHEMBL_JSON_ORDERING_POLICY_VERSION == "2026.05.30"
    assert len(CHEMBL_JSON_ORDERING_POLICY_HASH) == 64


def test_publication_profile_marks_reviewed_set_like_and_order_sensitive_fields() -> (
    None
):
    profile = resolve_normalization_profile("chembl", "publication")

    assert profile is not None
    assert "affiliation_list" in chembl_set_like_json_fields("chembl_publication")
    assert "authors" in chembl_order_sensitive_json_fields("chembl_publication")
    assert "affiliation_list" in profile.set_like_fields
    assert "authors" not in profile.set_like_fields
