"""Tests for canonical normalization profile registry helpers."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CROSSREF_PUBLICATION_PROFILE,
    PUBCHEM_COMPOUND_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
    build_normalization_profile_registry,
    normalize_normalization_profile_coordinates,
    resolve_normalization_profile,
)


def test_registry_contains_canonical_chembl_activity_profile() -> None:
    assert NORMALIZATION_PROFILE_REGISTRY[("chembl", "activity")] is CHEMBL_ACTIVITY_PROFILE
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("crossref", "publication")]
        is CROSSREF_PUBLICATION_PROFILE
    )
    assert NORMALIZATION_PROFILE_REGISTRY[("pubmed", "publication")] is PUBMED_PUBLICATION_PROFILE
    assert NORMALIZATION_PROFILE_REGISTRY[("pubchem", "compound")] is PUBCHEM_COMPOUND_PROFILE


def test_build_registry_matches_exported_registry() -> None:
    assert build_normalization_profile_registry() == NORMALIZATION_PROFILE_REGISTRY


def test_registry_contains_additional_publication_and_compound_profiles() -> None:
    assert NORMALIZATION_PROFILE_REGISTRY[("crossref", "publication")] is CROSSREF_PUBLICATION_PROFILE
    assert NORMALIZATION_PROFILE_REGISTRY[("pubmed", "publication")] is PUBMED_PUBLICATION_PROFILE
    assert NORMALIZATION_PROFILE_REGISTRY[("pubchem", "compound")] is PUBCHEM_COMPOUND_PROFILE


def test_normalize_coordinates_trims_and_lowercases() -> None:
    assert normalize_normalization_profile_coordinates(" ChEMBL ", " Activity ") == (
        "chembl",
        "activity",
    )


def test_normalize_coordinates_rejects_blank_entity() -> None:
    assert normalize_normalization_profile_coordinates("chembl", "   ") is None


def test_resolve_profile_uses_registry_coordinates() -> None:
    assert resolve_normalization_profile(" ChEMBL ", " Activity ") is CHEMBL_ACTIVITY_PROFILE
    assert (
        resolve_normalization_profile(" CrossRef ", " Publication ")
        is CROSSREF_PUBLICATION_PROFILE
    )
    assert resolve_normalization_profile("chembl", None) is None
