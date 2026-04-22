"""Tests for ChEMBL publication term normalization profile."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles import CHEMBL_PUBLICATION_TERM_PROFILE
from bioetl.domain.schemas.constants import PUBLICATION_TERM_TYPES


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("MESH_HEADING", "MESH_HEADING"),
        ("mesh_qualifier", "MESH_QUALIFIER"),
        (" keyword ", "KEYWORD"),
        ("concept", "CONCEPT"),
    ],
)
def test_publication_term_type_profile_canonicalizes_allowed_values(
    raw_value: str, expected: str
) -> None:
    rule = CHEMBL_PUBLICATION_TERM_PROFILE.field_rules["term_type"]

    assert rule.normalizer(raw_value) == expected


def test_publication_term_type_profile_rejects_unknown_values() -> None:
    rule = CHEMBL_PUBLICATION_TERM_PROFILE.field_rules["term_type"]

    assert rule.normalizer("AUTHOR") is None
    assert rule.normalizer("INSTITUTION") is None
    assert rule.normalizer("not-a-term-type") is None


def test_publication_term_type_uses_shared_schema_enum_source() -> None:
    rule = CHEMBL_PUBLICATION_TERM_PROFILE.field_rules["term_type"]

    assert PUBLICATION_TERM_TYPES == frozenset(
        {"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD", "CONCEPT"}
    )
    assert "enum" in (rule.notes or "").lower()
