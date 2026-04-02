"""Publication mapping registry data and query helpers."""

from __future__ import annotations

from typing import Final

from bioetl.domain.registry.publication_models import PublicationMapping

__all__ = [
    "ALL_PUBLICATION_ENTITY_TYPES",
    "LEGACY_PUBLICATION_ALIASES",
    "PUBLICATION_ENTITY_TYPES",
    "get_dedup_key_fields",
    "get_publication_entity_type_validation_error",
    "get_publication_mapping",
    "has_composite_key",
    "is_legacy_publication_alias",
    "is_publication_entity",
]

_PUBLICATION_MAPPINGS: Final[tuple[PublicationMapping, ...]] = (
    PublicationMapping(
        canonical_name="publication",
        api_resource="document",
        plural_key="documents",
        primary_key_field="publication_id",
    ),
    PublicationMapping(
        canonical_name="publication_similarity",
        api_resource="document_similarity",
        plural_key="document_similarities",
        primary_key_field="sim_id",
        primary_key_fields=("doc_1", "doc_2", "sim_id"),
    ),
    PublicationMapping(
        canonical_name="publication_term",
        api_resource="document",
        plural_key="documents",
        primary_key_field="publication_id",
        primary_key_fields=("publication_id", "term_type", "term"),
    ),
)

_PUBLICATION_MAPPING_INDEX: Final[dict[str, PublicationMapping]] = {
    mapping.canonical_name: mapping for mapping in _PUBLICATION_MAPPINGS
}

PUBLICATION_ENTITY_TYPES: Final[frozenset[str]] = frozenset(
    mapping.canonical_name
    for mapping in _PUBLICATION_MAPPINGS
    if not mapping.is_legacy_alias
)

LEGACY_PUBLICATION_ALIASES: Final[frozenset[str]] = frozenset(
    mapping.canonical_name
    for mapping in _PUBLICATION_MAPPINGS
    if mapping.is_legacy_alias
)

ALL_PUBLICATION_ENTITY_TYPES: Final[frozenset[str]] = frozenset(
    _PUBLICATION_MAPPING_INDEX.keys()
)


def get_publication_mapping(entity_type: str) -> PublicationMapping | None:
    """Get publication mapping for entity type.

    Args:
        entity_type: Canonical or legacy publication entity type name.

    Returns:
        PublicationMapping if found, None if entity type is unregistered.
    """
    return _PUBLICATION_MAPPING_INDEX.get(entity_type)


def is_publication_entity(entity_type: str) -> bool:
    """Check if entity type is a publication-related entity.

    Args:
        entity_type: Entity type name to check.

    Returns:
        True if entity type is registered in the publication mapping index.
    """
    return entity_type in _PUBLICATION_MAPPING_INDEX


def is_legacy_publication_alias(entity_type: str) -> bool:
    """Check if entity type is a legacy publication alias.

    Args:
        entity_type: Entity type name to check.

    Returns:
        True if entity type is a legacy alias (e.g., 'document' instead of 'publication').
    """
    return entity_type in LEGACY_PUBLICATION_ALIASES


def get_dedup_key_fields(entity_type: str) -> tuple[str, ...] | None:
    """Get composite key fields for deduplication.

    Args:
        entity_type: Canonical or legacy publication entity type name.

    Returns:
        Tuple of field names for deduplication, or None if entity type is unregistered.
    """
    mapping = get_publication_mapping(entity_type)
    if mapping is None:
        return None
    return mapping.get_dedup_key_fields()


def has_composite_key(entity_type: str) -> bool:
    """Check if entity type has a composite primary key.

    Args:
        entity_type: Entity type name to check.

    Returns:
        True if entity type uses a multi-field composite key for deduplication.
    """
    fields = get_dedup_key_fields(entity_type)
    return fields is not None and len(fields) > 1


def get_publication_entity_type_validation_error(
    entity_type: str, provider: str
) -> str | None:
    """Return the publication entity-type policy error for YAML configs.

    Args:
        entity_type: Entity type name from YAML config.
        provider: Provider name (only 'chembl' is subject to validation).

    Returns:
        Error message string if entity type is a disallowed legacy alias, None when
        the entity type is allowed for the given provider.
    """
    if provider != "chembl":
        return None
    if not is_legacy_publication_alias(entity_type):
        return None

    canonical_map = {
        "document": "publication",
        "document_similarity": "publication_similarity",
        "document_term": "publication_term",
    }
    canonical = canonical_map.get(entity_type)
    if canonical is None:
        return None

    return (
        f"YAML configs MUST use canonical name '{canonical}' instead of '{entity_type}'. "
        f"The '{entity_type}' name is a ChEMBL API-level detail and should not be used "
        f"directly in configuration files. See ADR-024 for details."
    )
