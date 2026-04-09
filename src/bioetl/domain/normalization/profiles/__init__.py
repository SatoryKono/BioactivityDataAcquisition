"""Provider/entity normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "FieldRule",
    "NormalizationProfile",
    "resolve_normalization_profile",
]


def resolve_normalization_profile(
    provider: str,
    entity_type: str | None,
) -> NormalizationProfile | None:
    """Resolve one shipped normalization profile by provider/entity."""
    normalized_provider = provider.strip().lower()
    normalized_entity = None if entity_type is None else entity_type.strip().lower()
    if normalized_provider == "chembl" and normalized_entity == "activity":
        return CHEMBL_ACTIVITY_PROFILE
    return None
