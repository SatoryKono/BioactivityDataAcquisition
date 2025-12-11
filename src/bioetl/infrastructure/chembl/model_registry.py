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
    # Note: "document" entity uses PublicationRawModel (canonical name)
    return {
        "activity": ActivityRawModel,
        "molecule": MoleculeRawModel,
        "target": TargetRawModel,
        "assay": AssayRawModel,
        "document": PublicationRawModel,  # Canonical: PublicationRawModel
    }


class ChemblEntityModelRegistry(EntityModelRegistryABC):
    """ChEMBL-specific entity model registry.

    Maps ChEMBL entity type names to their corresponding Pydantic
    domain models.

    Note:
        The "document" entity maps to PublicationRawModel (canonical name).
        DocumentRawModel is a deprecated alias.

    Example:
        >>> registry = ChemblEntityModelRegistry()
        >>> model_class = registry.get_model("document")
        >>> model_class.__name__
        'PublicationRawModel'
    """

    def get_model(self, entity: str) -> type[BaseModel]:
        """Get domain model class for entity type.

        Args:
            entity: Entity type name (activity, molecule, target, assay, document).

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
            Frozen set containing: activity, assay, target, molecule, document.
        """
        return frozenset(_get_entity_model_map().keys())


# Singleton instance for convenience
_default_registry: ChemblEntityModelRegistry | None = None


def get_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Get the default ChEMBL entity model registry instance.

    Returns:
        Singleton instance of ChemblEntityModelRegistry.

    Example:
        >>> registry = get_chembl_model_registry()
        >>> registry.is_supported("molecule")
        True
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ChemblEntityModelRegistry()
    return _default_registry


__all__ = [
    "ChemblEntityModelRegistry",
    "get_chembl_model_registry",
]
