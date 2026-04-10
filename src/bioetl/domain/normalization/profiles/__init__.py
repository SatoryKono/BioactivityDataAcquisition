"""Provider/entity normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
    build_normalization_profile_registry,
    normalize_normalization_profile_coordinates,
    resolve_normalization_profile,
)

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "NORMALIZATION_PROFILE_REGISTRY",
    "FieldRule",
    "NormalizationProfile",
    "build_normalization_profile_registry",
    "normalize_normalization_profile_coordinates",
    "resolve_normalization_profile",
]
