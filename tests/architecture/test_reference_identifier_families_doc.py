"""Doc governance for the non-ChEMBL reference identifier family registry."""

from __future__ import annotations

import pytest

from pathlib import Path

from bioetl.domain.normalization.reference_ids import reference_identifier_families

pytestmark = pytest.mark.architecture

DOC_PATH = Path("docs/03-data-model/reference-identifier-families.md")


def test_reference_identifier_family_doc_lists_all_governed_families() -> None:
    actual = DOC_PATH.read_text(encoding="utf-8")

    assert "# Reference Identifier Families" in actual
    assert "domain.normalization.reference_ids" in actual

    for family in reference_identifier_families():
        assert f"`{family.name}`" in actual
        assert family.storage_representation.replace("_", " ") in actual
        semantics_variants = {
            family.collection_semantics,
            family.collection_semantics.replace("_", "-"),
            family.collection_semantics.replace("_", " "),
            family.collection_semantics.replace("_or_", " or ").replace("_", "-"),
            family.collection_semantics.replace("_or_", " or ").replace("_", " "),
        }
        assert any(variant in actual for variant in semantics_variants)


def test_reference_identifier_family_registry_keeps_stable_nonempty_metadata() -> None:
    families = reference_identifier_families()

    assert families
    assert len({family.name for family in families}) == len(families)

    for family in families:
        assert family.description
        assert family.storage_representation
        assert family.collection_semantics
