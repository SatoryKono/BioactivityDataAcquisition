"""ChEMBL entity model registry implementation.

This module provides the concrete implementation of EntityModelRegistryABC
for ChEMBL entities, mapping entity type names to their Pydantic models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from bioetl.domain.ports.entity_models import EntityModelRegistryABC

if TYPE_CHECKING:
    pass


def _get_entity_model_map() -> dict[str, type[BaseModel]]:
    """Lazy import of domain models to avoid module-level import."""
    from bioetl.domain.schemas.chembl.raw_models import (
        ActivityRawModel,
        AssayRawModel,
        MoleculeRawModel,
        PublicationRawModel,
        TargetRawModel,
    )

    # Internal mapping of entity type -> model class
    # Note: Both "document" and "publication" entities use PublicationRawModel
    # "publication" is the domain name, "document" is the ChEMBL API endpoint name
    return {
        "activity": ActivityRawModel,
        "molecule": MoleculeRawModel,
        "target": TargetRawModel,
        "assay": AssayRawModel,
        "document": PublicationRawModel,  # ChEMBL API endpoint name
        "publication": PublicationRawModel,  # Domain canonical name
    }


class ChemblEntityModelRegistry(EntityModelRegistryABC):
    """ChEMBL-specific entity model registry.

    Maps ChEMBL entity type names to their corresponding Pydantic
    domain models.

    Note:
        Both "document" (ChEMBL API endpoint) and "publication" (domain canonical name)
        map to PublicationRawModel.

    Example:
        >>> registry = ChemblEntityModelRegistry()
        >>> model_class = registry.get_model("publication")
        >>> model_class.__name__
        'PublicationRawModel'
        >>> registry.get_model("document").__name__
        'PublicationRawModel'
    """

    def get_model(self, entity: str) -> type[BaseModel]:
        """Get domain model class for entity type.

        Args:
            entity: Entity type name (activity, molecule, target, assay,
                document, publication).

        Returns:
            Pydantic model class for the entity.

        Raises:
            ValueError: If entity type is unknown.

        Example:
            >>> registry = ChemblEntityModelRegistry()
            >>> model_class = registry.get_model("activity")
            >>> model_class.__name__
            'ActivityRawModel'
        """
        entity_map = _get_entity_model_map()
        model_class = entity_map.get(entity)
        if model_class is None:
            raise ValueError(
                f"Unknown entity type: {entity}. "
                f"Supported: {sorted(entity_map.keys())}"
            )
        return model_class

    def is_supported(self, entity: str) -> bool:
        """Check if entity type has a registered model.

        Args:
            entity: Entity type name to check.

        Returns:
            True if entity has a registered model, False otherwise.
        """
        return entity in _get_entity_model_map()

    def supported_entities(self) -> frozenset[str]:
        """Return set of supported entity names.

        Returns:
            Frozen set containing: activity, assay, target, molecule,
            document, publication.
        """
        return frozenset(_get_entity_model_map().keys())


# =============================================================================
# Factory and default instance management
# =============================================================================

_default_registry: ChemblEntityModelRegistry | None = None


def create_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Factory function for creating a new ChemblEntityModelRegistry instance.

    Use this for dependency injection or when you need an isolated instance.

    Returns:
        A new ChemblEntityModelRegistry instance.

    Example:
        >>> registry = create_chembl_model_registry()
        >>> registry.is_supported("molecule")
        True
    """
    return ChemblEntityModelRegistry()


def get_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Get or create the default ChEMBL entity model registry instance.

    This function provides lazy initialization of a shared registry instance.
    For dependency injection, prefer using create_chembl_model_registry().

    Returns:
        The default ChemblEntityModelRegistry instance.

    Example:
        >>> registry = get_chembl_model_registry()
        >>> registry.is_supported("molecule")
        True
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = create_chembl_model_registry()
    return _default_registry


def reset_chembl_model_registry() -> None:
    """Reset the default registry instance (for testing).

    This clears the cached default instance. The next call to
    get_chembl_model_registry() will create a fresh instance.
    """
    global _default_registry
    _default_registry = None


__all__ = [
    "ChemblEntityModelRegistry",
    "create_chembl_model_registry",
    "get_chembl_model_registry",
    "reset_chembl_model_registry",
]
