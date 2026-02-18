"""Domain layer registries.

Centralized registries for entity type mappings and configuration.
These registries provide a single source of truth for entity metadata.

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- ADR-024: Entity naming unification (publication* → document*)
"""

from __future__ import annotations

from bioetl.domain.registry.field_aliases import (
    MOLECULE_FIELD_ALIASES,
    FieldAlias,
    get_all_aliases_for_provider,
    get_canonical_name,
    get_provider_name,
)
from bioetl.domain.registry.publication import (
    LEGACY_PUBLICATION_ALIASES,
    PUBLICATION_ENTITY_TYPES,
    PublicationMapping,
    get_publication_mapping,
    is_legacy_publication_alias,
    is_publication_entity,
    validate_publication_entity_type,
)

__all__ = [
    "LEGACY_PUBLICATION_ALIASES",
    "MOLECULE_FIELD_ALIASES",
    "PUBLICATION_ENTITY_TYPES",
    "FieldAlias",
    "PublicationMapping",
    "get_all_aliases_for_provider",
    "get_canonical_name",
    "get_provider_name",
    "get_publication_mapping",
    "is_legacy_publication_alias",
    "is_publication_entity",
    "validate_publication_entity_type",
]  # RUF022: sorted by category (constants, classes, functions)
