"""Canonical registry for shipped normalization profiles."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
)
from bioetl.domain.normalization.profiles.crossref_publication import (
    CROSSREF_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
)
from bioetl.domain.normalization.profiles.pubmed_publication import (
    PUBMED_PUBLICATION_PROFILE,
)

__all__ = [
    "NORMALIZATION_PROFILE_REGISTRY",
    "build_normalization_profile_registry",
    "normalize_normalization_profile_coordinates",
    "resolve_normalization_profile",
]


def normalize_normalization_profile_coordinates(
    provider: str,
    entity_type: str | None,
) -> tuple[str, str] | None:
    """Return canonical provider/entity coordinates for profile lookup."""
    normalized_provider = provider.strip().lower()
    normalized_entity = None if entity_type is None else entity_type.strip().lower()
    if not normalized_provider or normalized_entity is None or not normalized_entity:
        return None
    return normalized_provider, normalized_entity


def build_normalization_profile_registry() -> Mapping[tuple[str, str], NormalizationProfile]:
    """Return the immutable registry of shipped normalization profiles."""
    return {
        ("chembl", "activity"): CHEMBL_ACTIVITY_PROFILE,
        ("crossref", "publication"): CROSSREF_PUBLICATION_PROFILE,
        ("pubchem", "compound"): PUBCHEM_COMPOUND_PROFILE,
        ("pubmed", "publication"): PUBMED_PUBLICATION_PROFILE,
    }


NORMALIZATION_PROFILE_REGISTRY = build_normalization_profile_registry()


def resolve_normalization_profile(
    provider: str,
    entity_type: str | None,
) -> NormalizationProfile | None:
    """Resolve one shipped normalization profile by provider/entity."""
    coordinates = normalize_normalization_profile_coordinates(provider, entity_type)
    if coordinates is None:
        return None
    return NORMALIZATION_PROFILE_REGISTRY.get(coordinates)
