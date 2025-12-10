"""Registry mapping entity types to domain models (application layer).

This module contains the entity-to-model mapping that belongs in the application
layer, not infrastructure. The mapping is domain knowledge that should be
decoupled from infrastructure parsing concerns.
"""

from __future__ import annotations

from pydantic import BaseModel

from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    DocumentRawModel,
    MoleculeRawModel,
    TargetRawModel,
)

# Mapping entity type -> model class
ENTITY_MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "activity": ActivityRawModel,
    "molecule": MoleculeRawModel,
    "target": TargetRawModel,
    "assay": AssayRawModel,
    "document": DocumentRawModel,
}


def get_model_for_entity(entity: str) -> type[BaseModel]:
    """Get domain model class for entity type.

    Args:
        entity: Entity type name (activity, molecule, target, assay, document).

    Returns:
        Pydantic model class for the entity.

    Raises:
        ValueError: If entity type is unknown.

    Example:
        >>> model_class = get_model_for_entity("activity")
        >>> model_class.__name__
        'ActivityRawModel'
    """
    model_class = ENTITY_MODEL_REGISTRY.get(entity)
    if model_class is None:
        raise ValueError(
            f"Unknown entity type: {entity}. "
            f"Supported: {sorted(ENTITY_MODEL_REGISTRY.keys())}"
        )
    return model_class


def is_registered_entity(entity: str) -> bool:
    """Check if entity type has a registered model.

    Args:
        entity: Entity type name to check.

    Returns:
        True if entity has a registered model, False otherwise.
    """
    return entity in ENTITY_MODEL_REGISTRY


__all__ = [
    "ENTITY_MODEL_REGISTRY",
    "get_model_for_entity",
    "is_registered_entity",
]
