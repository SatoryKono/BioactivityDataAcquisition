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


class _RegistryHolder:
    """Thread-safe holder for singleton registry instance.

    Uses class-level attribute instead of module-level global to
    improve encapsulation and testability.
    """

    _instance: ChemblEntityModelRegistry | None = None

    @classmethod
    def get_or_create(cls) -> ChemblEntityModelRegistry:
        """Get or create the singleton registry instance."""
        if cls._instance is None:
            cls._instance = ChemblEntityModelRegistry()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None


def get_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Get the default ChEMBL entity model registry instance.

    Returns:
        Singleton instance of ChemblEntityModelRegistry.

    Example:
        >>> registry = get_chembl_model_registry()
        >>> registry.is_supported("molecule")
        True
    """
    return _RegistryHolder.get_or_create()


def reset_chembl_model_registry() -> None:
    """Reset the registry singleton (for testing).

    This allows tests to start with a fresh registry instance.
    """
    _RegistryHolder.reset()


__all__ = [
    "ChemblEntityModelRegistry",
    "get_chembl_model_registry",
    "reset_chembl_model_registry",
]
