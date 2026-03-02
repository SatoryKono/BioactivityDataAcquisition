"""Publication entity mapping registry.

Centralized registry for publication entity type mappings to ChEMBL API resources.
This module is the single source of truth for all publication-related entity mappings.

Architecture Notes:
    - **Canonical names**: `publication`, `publication_term`, `publication_similarity`
      are the domain-level entity types used in YAML configs and pipeline code.

    - **API resources**: `document`, `document_similarity` are ChEMBL API-level
      implementation details. YAML configs MUST NOT use these directly.

    - **Legacy aliases**: `document*` names are kept ONLY for backward compatibility
      and should NOT be used in new code.

Requirements:
    - REQ-ARCH-003: No I/O in domain layer (only immutable data structures)
    - ADR-024: Entity naming unification

See Also:
    - `infrastructure/adapters/chembl/entity_mapper.py`: Uses this registry
    - `docs/02-architecture/decisions/ADR-024-entity-naming-unification.md`

Example:
    >>> from bioetl.domain.registry import get_publication_mapping, is_publication_entity
    >>> mapping = get_publication_mapping("publication")
    >>> mapping.api_resource
    'document'
    >>> is_publication_entity("publication_term")
    True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class PublicationMapping:
    """Immutable mapping from canonical publication entity to ChEMBL API details.

    This value object encapsulates all metadata needed to interact with ChEMBL API
    for a publication-related entity type.

    Attributes:
        canonical_name: Domain-level entity type (e.g., 'publication').
                       This is what YAML configs and pipeline code should use.
        api_resource: ChEMBL API resource name (e.g., 'document').
                     This is an API-level implementation detail.
        plural_key: Key for extracting records from API response (e.g., 'documents').
        primary_key_field: Primary key field for deduplication (single field).
                          Use primary_key_fields for composite keys.
        primary_key_fields: Composite primary key fields for deduplication.
                           When set, deduplication uses all fields together.
                           Defaults to (primary_key_field,) for backward compatibility.
        is_legacy_alias: True if this is a backward-compatibility alias.
                        Legacy aliases should NOT be used in new code.

    Note:
        The `api_resource` and `plural_key` fields are ChEMBL API implementation
        details and should be treated as such. Domain code should work with
        `canonical_name` only.

    Example:
        For publication_term, the composite key is (document_chembl_id, term_type, term)
        which ensures each unique term within a document is deduplicated correctly.
    """

    canonical_name: str
    api_resource: str
    plural_key: str
    primary_key_field: str
    primary_key_fields: tuple[str, ...] | None = None
    is_legacy_alias: bool = False

    def get_dedup_key_fields(self) -> tuple[str, ...]:
        """Get the fields to use for deduplication.

        Returns composite key fields if defined, otherwise single primary key field.

        Returns:
            Tuple of field names for deduplication.
        """
        if self.primary_key_fields is not None:
            return self.primary_key_fields
        return (self.primary_key_field,)


# =============================================================================
# Publication Entity Registry
# =============================================================================
# Single source of truth for publication entity mappings.
# YAML configs MUST use canonical names (publication*).
# document* names are API-level details, NOT domain entities.

_PUBLICATION_MAPPINGS: Final[tuple[PublicationMapping, ...]] = (
    # Canonical publication entity types (ADR-024)
    # Use these in YAML configs and pipeline code.
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
        # sim_id is already unique for each document pair
        # Composite key ensures deterministic deduplication
        primary_key_fields=("doc_1", "doc_2", "sim_id"),
    ),
    PublicationMapping(
        canonical_name="publication_term",
        api_resource="document",  # Derived from publication endpoint
        plural_key="documents",
        primary_key_field="publication_id",
        # Composite key for uniqueness: document + term type + term text
        # Note: entity_id is SHA256 hash of this composite key
        primary_key_fields=("publication_id", "term_type", "term"),
    ),
    # Legacy aliases (backward compatibility ONLY)
    # DO NOT use in new code. Will be deprecated.
    PublicationMapping(
        canonical_name="document",
        api_resource="document",
        plural_key="documents",
        primary_key_field="document_chembl_id",
        is_legacy_alias=True,
    ),
    PublicationMapping(
        canonical_name="document_similarity",
        api_resource="document_similarity",
        plural_key="document_similarities",
        primary_key_field="sim_id",
        primary_key_fields=("doc_1", "doc_2", "sim_id"),
        is_legacy_alias=True,
    ),
    PublicationMapping(
        canonical_name="document_term",
        api_resource="document",
        plural_key="documents",
        primary_key_field="document_chembl_id",
        primary_key_fields=("document_chembl_id", "term_type", "term"),
        is_legacy_alias=True,
    ),
)

# Index by entity type for O(1) lookup
_PUBLICATION_MAPPING_INDEX: Final[dict[str, PublicationMapping]] = {
    mapping.canonical_name: mapping for mapping in _PUBLICATION_MAPPINGS
}

# Set of canonical (non-legacy) publication entity types
PUBLICATION_ENTITY_TYPES: Final[frozenset[str]] = frozenset(
    mapping.canonical_name
    for mapping in _PUBLICATION_MAPPINGS
    if not mapping.is_legacy_alias
)

# Set of legacy aliases (for deprecation warnings)
LEGACY_PUBLICATION_ALIASES: Final[frozenset[str]] = frozenset(
    mapping.canonical_name
    for mapping in _PUBLICATION_MAPPINGS
    if mapping.is_legacy_alias
)

# All registered entity types (canonical + legacy)
ALL_PUBLICATION_ENTITY_TYPES: Final[frozenset[str]] = frozenset(
    _PUBLICATION_MAPPING_INDEX.keys()
)


def get_publication_mapping(entity_type: str) -> PublicationMapping | None:
    """Get publication mapping for entity type.

    Args:
        entity_type: Entity type to look up (e.g., 'publication').

    Returns:
        PublicationMapping if entity_type is a publication entity, None otherwise.

    Example:
        >>> mapping = get_publication_mapping("publication")
        >>> mapping.api_resource
        'document'
        >>> mapping.primary_key_field
        'document_chembl_id'
    """
    return _PUBLICATION_MAPPING_INDEX.get(entity_type)


def is_publication_entity(entity_type: str) -> bool:
    """Check if entity type is a publication-related entity.

    Includes both canonical names and legacy aliases.

    Args:
        entity_type: Entity type to check.

    Returns:
        True if entity_type is a publication entity (canonical or legacy).

    Example:
        >>> is_publication_entity("publication")
        True
        >>> is_publication_entity("document")  # Legacy alias
        True
        >>> is_publication_entity("activity")
        False
    """
    return entity_type in _PUBLICATION_MAPPING_INDEX


def is_legacy_publication_alias(entity_type: str) -> bool:
    """Check if entity type is a legacy publication alias.

    Legacy aliases (document*) are kept for backward compatibility only.
    New code should use canonical names (publication*).

    Args:
        entity_type: Entity type to check.

    Returns:
        True if entity_type is a legacy alias.

    Example:
        >>> is_legacy_publication_alias("document")
        True
        >>> is_legacy_publication_alias("publication")
        False
    """
    return entity_type in LEGACY_PUBLICATION_ALIASES


def get_dedup_key_fields(entity_type: str) -> tuple[str, ...] | None:
    """Get composite key fields for deduplication.

    Returns the fields that should be used together for deduplication.
    For entities with composite keys (like publication_term), returns
    all fields in the composite key. For simple entities, returns
    the single primary key field as a tuple.

    Args:
        entity_type: Entity type to look up (e.g., 'publication_term').

    Returns:
        Tuple of field names for deduplication, or None if not a publication entity.

    Example:
        >>> get_dedup_key_fields("publication_term")
        ('document_chembl_id', 'term_type', 'term')
        >>> get_dedup_key_fields("publication")
        ('document_chembl_id',)
        >>> get_dedup_key_fields("activity")
        None
    """
    mapping = get_publication_mapping(entity_type)
    if mapping is None:
        return None
    return mapping.get_dedup_key_fields()


def has_composite_key(entity_type: str) -> bool:
    """Check if entity type has a composite primary key.

    Returns True if the entity uses multiple fields for deduplication.

    Args:
        entity_type: Entity type to check.

    Returns:
        True if entity has composite key (more than one field).

    Example:
        >>> has_composite_key("publication_term")
        True
        >>> has_composite_key("publication")
        False
    """
    fields = get_dedup_key_fields(entity_type)
    return fields is not None and len(fields) > 1


def validate_publication_entity_type(entity_type: str, provider: str) -> str | None:
    """Validate publication entity type in YAML configs.

    Checks that YAML configs use canonical publication names (publication*)
    instead of API-level names (document*) for ChEMBL provider.

    This function is intended for use in config validation (Pydantic validators).

    Args:
        entity_type: Entity type from YAML config.
        provider: Provider name (e.g., 'chembl').

    Returns:
        Error message if validation fails, None if valid.

    Example:
        >>> validate_publication_entity_type("document", "chembl")
        "YAML configs MUST use canonical name 'publication' instead of 'document'. ..."
        >>> validate_publication_entity_type("publication", "chembl")
        None
    """
    # Only validate for ChEMBL provider (other providers may use document differently)
    if provider != "chembl":
        return None

    # Check if using legacy alias
    if not is_legacy_publication_alias(entity_type):
        return None

    # Find canonical equivalent
    canonical_map = {
        "document": "publication",
        "document_similarity": "publication_similarity",
        "document_term": "publication_term",
    }

    canonical = canonical_map.get(entity_type)
    if canonical is None:
        return None  # Unknown alias, let other validation handle it

    return (
        f"YAML configs MUST use canonical name '{canonical}' instead of '{entity_type}'. "
        f"The '{entity_type}' name is a ChEMBL API-level detail and should not be used "
        f"directly in configuration files. See ADR-024 for details."
    )
