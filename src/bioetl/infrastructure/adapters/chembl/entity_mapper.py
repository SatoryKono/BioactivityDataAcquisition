"""ChEMBL entity mapping utilities.

Provides entity type to API resource mapping and primary key resolution.
Extracted from chembl/client.py for better separation of concerns.

Architecture Notes:
    Publication entity mappings (publication* → document*) are sourced from
    the centralized domain registry (domain/registry/publication.py).
    This module provides a unified API for all ChEMBL entity types.

    - **Canonical names** (publication*): Use in YAML configs and pipeline code.
    - **API resources** (document*): ChEMBL API implementation details.
      YAML configs MUST NOT use document* directly.

Requirements:
    - ADR-024: Entity naming unification
    - Single source of truth for publication mappings in domain.registry

See Also:
    - domain/registry/publication.py: Publication mapping registry
    - docs/02-architecture/decisions/ADR-024-entity-naming-unification.md
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.chembl._entity_mapping_lookup import (
    build_legacy_entity_mapping,
    has_entity_composite_key,
    is_known_entity_type,
    resolve_dedup_key_fields,
    resolve_plural_key,
    resolve_primary_key_field,
    resolve_resource_name,
)
from bioetl.infrastructure.adapters.chembl.constants import (
    CHEMBL_API_BASE,
)

__all__ = ["ENTITY_MAPPING", "ENTITY_MAPPING_LIFECYCLE", "ChemblEntityMapper"]


class ChemblEntityMapper:
    """Maps entity types to ChEMBL API resources and primary keys.

    This class provides a unified interface for resolving:
    - API resource URLs (e.g., 'publication' → '/document')
    - Response plural keys (e.g., 'publication' → 'documents')
    - Primary key fields (e.g., 'publication' → 'document_chembl_id')

    Publication entity mappings are sourced from the centralized domain registry
    (domain/registry/publication.py), ensuring a single source of truth.

    Note:
        - Use canonical names (publication*) in YAML configs
        - document* names are API-level details and should NOT be used directly
        - Legacy aliases (document*) are supported for backward compatibility
    """

    @staticmethod
    def get_resource_url(entity_type: str) -> str:
        """Get ChEMBL API URL for entity type.

        Args:
            entity_type: Entity type (e.g., 'activity', 'assay', 'publication').
                        Use canonical names from YAML configs.

        Returns:
            Full API URL for the entity resource (without .json extension).

        Raises:
            ValueError: If entity type is unknown.

        Note:
            ChEMBL API no longer supports .json extension.
            Use format=json query parameter instead (added by _build_params).

        Example:
            >>> ChemblEntityMapper.get_resource_url("publication")
            'https://www.ebi.ac.uk/chembl/api/data/document'
        """
        resource = resolve_resource_name(entity_type)
        if resource is None:
            msg = f"Unknown entity type: {entity_type}"
            raise ValueError(msg)
        return f"{CHEMBL_API_BASE}/{resource}"

    @staticmethod
    def get_direct_record_url(entity_type: str, record_id: str) -> str:
        """Get direct URL for fetching a single record by ID.

        ChEMBL API supports two ways to fetch records:
        1. Filter endpoint: /target?target_chembl_id__in=CHEMBL123
        2. Direct endpoint: /target/CHEMBL123

        The direct endpoint uses different server-side code paths and may work
        when the filter endpoint fails with 500 errors.

        Args:
            entity_type: Entity type (e.g., 'target', 'molecule').
            record_id: The ChEMBL ID of the record (e.g., 'CHEMBL1075105').

        Returns:
            Direct API URL for the single record.

        Example:
            >>> ChemblEntityMapper.get_direct_record_url("target", "CHEMBL1075105")
            'https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL1075105'
        """
        base_url = ChemblEntityMapper.get_resource_url(entity_type)
        return f"{base_url}/{record_id}"

    @staticmethod
    def get_plural_key(entity_type: str) -> str:
        """Get the plural form key for API response parsing.

        Args:
            entity_type: Entity type (e.g., 'activity', 'publication').

        Returns:
            Plural key for extracting records from response.

        Example:
            >>> ChemblEntityMapper.get_plural_key("publication")
            'documents'
        """
        return resolve_plural_key(entity_type)

    @staticmethod
    def get_primary_key_field(entity_type: str) -> str:
        """Get the primary key field name for deduplication.

        Args:
            entity_type: Entity type (e.g., 'activity', 'publication').

        Returns:
            Primary key field name.

        Example:
            >>> ChemblEntityMapper.get_primary_key_field("publication")
            'document_chembl_id'
        """
        return resolve_primary_key_field(entity_type)

    @staticmethod
    def get_dedup_key_fields(entity_type: str) -> tuple[str, ...]:
        """Get the composite key fields for deduplication.

        For entities with composite primary keys (like publication_term),
        returns all fields that together form the unique key.
        For entities with single primary key, returns a tuple with that field.

        Args:
            entity_type: Entity type (e.g., 'publication_term', 'activity').

        Returns:
            Tuple of field names for deduplication.

        Example:
            >>> ChemblEntityMapper.get_dedup_key_fields("publication_term")
            ('document_chembl_id', 'term_type', 'term')
            >>> ChemblEntityMapper.get_dedup_key_fields("activity")
            ('activity_id',)
        """
        return resolve_dedup_key_fields(entity_type)

    @staticmethod
    def has_composite_key(entity_type: str) -> bool:
        """Check if entity type has a composite primary key.

        Args:
            entity_type: Entity type to check.

        Returns:
            True if entity uses multiple fields for deduplication.

        Example:
            >>> ChemblEntityMapper.has_composite_key("publication_term")
            True
            >>> ChemblEntityMapper.has_composite_key("activity")
            False
        """
        return has_entity_composite_key(entity_type)

    @staticmethod
    def get_resource_name(entity_type: str) -> str | None:
        """Get the ChEMBL resource name for entity type.

        Args:
            entity_type: Entity type (e.g., 'activity', 'publication').

        Returns:
            Resource name or None if unknown.

        Example:
            >>> ChemblEntityMapper.get_resource_name("publication")
            'document'
        """
        return resolve_resource_name(entity_type)

    @staticmethod
    def is_known_entity(entity_type: str) -> bool:
        """Check if entity type is known (publication or non-publication).

        Args:
            entity_type: Entity type to check.

        Returns:
            True if entity type is recognized.

        Example:
            >>> ChemblEntityMapper.is_known_entity("publication")
            True
            >>> ChemblEntityMapper.is_known_entity("unknown")
            False
        """
        return is_known_entity_type(entity_type)


# =============================================================================
# Backward Compatibility Alias
# =============================================================================
# Deprecated public alias retained for external compatibility only.
# First-party code MUST use ChemblEntityMapper / resolve_resource_name instead.
# Lifecycle is inventoried in configs/quality/chembl_entity_mapping_compatibility.yaml
# and ratcheted by tests/architecture/test_chembl_entity_mapping_lifecycle.py (#7495).

ENTITY_MAPPING_LIFECYCLE: dict[str, object] = {
    "symbol": "ENTITY_MAPPING",
    "module": "bioetl.infrastructure.adapters.chembl.entity_mapper",
    "status": "retained_external_compatibility",
    "owner": "bioetl.infrastructure.adapters.chembl",
    "consumer_class": "external_unspecified",
    "canonical_target": (
        "bioetl.infrastructure.adapters.chembl.entity_mapper.ChemblEntityMapper "
        "/ bioetl.infrastructure.adapters.chembl._entity_mapping_lookup."
        "build_legacy_entity_mapping / resolve_resource_name"
    ),
    "sunset_status": "retained_until_external_migration_evidence",
    "review_date": "2026-09-30",
    "external_breaking_change_required": True,
    "internal_callers_zero": True,
    "max_src_importer_count": 0,
    "migration_path": (
        "Replace ENTITY_MAPPING[entity] lookups with "
        "ChemblEntityMapper.get_resource_url(entity) or resolve_resource_name(entity)."
    ),
    "exit_criteria": (
        "Remove the alias only after importer census shows zero external consumers "
        "or a coordinated major-version breaking-change notice is published."
    ),
    "linked_issue": 7495,
}

ENTITY_MAPPING: dict[str, str] = build_legacy_entity_mapping()
