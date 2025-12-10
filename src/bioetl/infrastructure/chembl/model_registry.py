"""ChEMBL entity model registry implementation.

This module provides the concrete implementation of EntityModelRegistryABC
for ChEMBL entities, mapping entity type names to their Pydantic models.
"""

from __future__ import annotations

from pydantic import BaseModel

from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    DocumentRawModel,
    MoleculeRawModel,
    TargetRawModel,
)

# Internal mapping of entity type -> model class
_ENTITY_MODEL_MAP: dict[str, type[BaseModel]] = {
    "activity": ActivityRawModel,
    "molecule": MoleculeRawModel,
    "target": TargetRawModel,
    "assay": AssayRawModel,
    "document": DocumentRawModel,
}


class ChemblEntityModelRegistry(EntityModelRegistryABC):
    """ChEMBL-specific entity model registry.

    Maps ChEMBL entity type names to their corresponding Pydantic
    domain models.

    Example:
        >>> registry = ChemblEntityModelRegistry()
        >>> model_class = registry.get_model("activity")
        >>> model_class.__name__
        'ActivityRawModel'
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
        model_class = _ENTITY_MODEL_MAP.get(entity)
        if model_class is None:
            raise ValueError(
                f"Unknown entity type: {entity}. "
                f"Supported: {sorted(_ENTITY_MODEL_MAP.keys())}"
            )
        return model_class

    def is_supported(self, entity: str) -> bool:
        """Check if entity type has a registered model.

        Args:
            entity: Entity type name to check.

        Returns:
            True if entity has a registered model, False otherwise.
        """
        return entity in _ENTITY_MODEL_MAP

    def supported_entities(self) -> frozenset[str]:
        """Return set of supported entity names.

        Returns:
            Frozen set containing: activity, assay, target, molecule, document.
        """
        return frozenset(_ENTITY_MODEL_MAP.keys())


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
