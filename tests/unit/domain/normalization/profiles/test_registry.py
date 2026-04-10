"""Tests for canonical normalization profile registry helpers."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import CHEMBL_ACTIVITY_PROFILE
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
    build_normalization_profile_registry,
    normalize_normalization_profile_coordinates,
    resolve_normalization_profile,
)


def test_registry_contains_canonical_chembl_activity_profile() -> None:
    assert NORMALIZATION_PROFILE_REGISTRY[("chembl", "activity")] is CHEMBL_ACTIVITY_PROFILE


def test_build_registry_matches_exported_registry() -> None:
    assert build_normalization_profile_registry() == NORMALIZATION_PROFILE_REGISTRY


def test_normalize_coordinates_trims_and_lowercases() -> None:
    assert normalize_normalization_profile_coordinates(" ChEMBL ", " Activity ") == (
        "chembl",
        "activity",
    )


def test_normalize_coordinates_rejects_blank_entity() -> None:
    assert normalize_normalization_profile_coordinates("chembl", "   ") is None


def test_resolve_profile_uses_registry_coordinates() -> None:
    assert resolve_normalization_profile(" ChEMBL ", " Activity ") is CHEMBL_ACTIVITY_PROFILE
    assert resolve_normalization_profile("chembl", None) is None
