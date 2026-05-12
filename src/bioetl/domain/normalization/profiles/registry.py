"""Canonical registry for shipped normalization profiles."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.normalization.profiles._registry_declarations import (
    NORMALIZATION_PROFILE_DECLARATIONS,
)
from bioetl.domain.normalization.profiles.base import (
    NormalizationProfile,
    NormalizationProfileIdentity,
)

__all__ = [
    "NORMALIZATION_PROFILE_IDENTITIES",
    "NORMALIZATION_PROFILE_MODULE_PATHS",
    "NORMALIZATION_PROFILE_REGISTRY",
    "build_normalization_profile_identities",
    "build_normalization_profile_module_paths",
    "build_normalization_profile_registry",
    "normalize_normalization_profile_coordinates",
    "resolve_normalization_profile",
    "resolve_normalization_profile_identity",
    "resolve_normalization_profile_module_path",
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


def _resolve_normalization_profile_value[TValue](
    mapping: Mapping[tuple[str, str], TValue],
    provider: str,
    entity_type: str | None,
) -> TValue | None:
    """Resolve one canonical registry value by provider/entity coordinates."""
    coordinates = normalize_normalization_profile_coordinates(provider, entity_type)
    if coordinates is None:
        return None
    return mapping.get(coordinates)


def build_normalization_profile_registry() -> Mapping[
    tuple[str, str], NormalizationProfile
]:
    """Return the immutable registry of shipped normalization profiles."""
    return {
        (declaration.provider, declaration.entity_type): declaration.profile
        for declaration in NORMALIZATION_PROFILE_DECLARATIONS
    }


def build_normalization_profile_identities() -> Mapping[
    tuple[str, str], NormalizationProfileIdentity
]:
    """Return deterministic identities for shipped normalization profiles."""
    return {
        coordinates: profile.identity
        for coordinates, profile in build_normalization_profile_registry().items()
    }


def build_normalization_profile_module_paths() -> Mapping[tuple[str, str], str]:
    """Return canonical source-module paths for shipped normalization profiles."""
    return {
        (declaration.provider, declaration.entity_type): declaration.module_path
        for declaration in NORMALIZATION_PROFILE_DECLARATIONS
    }


NORMALIZATION_PROFILE_REGISTRY = build_normalization_profile_registry()
NORMALIZATION_PROFILE_IDENTITIES = build_normalization_profile_identities()
NORMALIZATION_PROFILE_MODULE_PATHS = build_normalization_profile_module_paths()


def resolve_normalization_profile(
    provider: str,
    entity_type: str | None,
) -> NormalizationProfile | None:
    """Resolve one shipped normalization profile by provider/entity."""
    return _resolve_normalization_profile_value(
        NORMALIZATION_PROFILE_REGISTRY,
        provider,
        entity_type,
    )


def resolve_normalization_profile_identity(
    provider: str,
    entity_type: str | None,
) -> NormalizationProfileIdentity | None:
    """Resolve one shipped normalization profile identity by provider/entity."""
    return _resolve_normalization_profile_value(
        NORMALIZATION_PROFILE_IDENTITIES,
        provider,
        entity_type,
    )


def resolve_normalization_profile_module_path(
    provider: str,
    entity_type: str | None,
) -> str | None:
    """Resolve one shipped normalization profile source-module path by provider/entity."""
    return _resolve_normalization_profile_value(
        NORMALIZATION_PROFILE_MODULE_PATHS,
        provider,
        entity_type,
    )
