"""Publication entity mapping registry facade."""

from __future__ import annotations

from bioetl.domain.registry.publication_data import (
    ALL_PUBLICATION_ENTITY_TYPES,
    LEGACY_PUBLICATION_ALIASES,
    PUBLICATION_ENTITY_TYPES,
    get_dedup_key_fields,
    get_publication_entity_type_validation_error,
    get_publication_mapping,
    has_composite_key,
    is_legacy_publication_alias,
    is_publication_entity,
)
from bioetl.domain.registry.publication_models import PublicationMapping

__all__ = [
    "ALL_PUBLICATION_ENTITY_TYPES",
    "LEGACY_PUBLICATION_ALIASES",
    "PUBLICATION_ENTITY_TYPES",
    "PublicationMapping",
    "get_dedup_key_fields",
    "get_publication_entity_type_validation_error",
    "get_publication_mapping",
    "has_composite_key",
    "is_legacy_publication_alias",
    "is_publication_entity",
]
