"""Registry for ChEMBL entity parsers."""

from typing import Literal, TypeAlias

from pydantic import BaseModel

from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    DocumentRawModel,
    MoleculeRawModel,
    TargetRawModel,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)

ChemblEntityType: TypeAlias = Literal[
    "activity", "molecule", "target", "assay", "document"
]

# Mapping entity type -> model class
ENTITY_MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "activity": ActivityRawModel,
    "molecule": MoleculeRawModel,
    "target": TargetRawModel,
    "assay": AssayRawModel,
    "document": DocumentRawModel,
}


def get_model_for_entity(entity: str) -> type[BaseModel]:
    """
    Get model class for entity type.

    Args:
        entity: Entity type name (activity, molecule, target, assay, document).

    Returns:
        Pydantic model class for the entity.

    Raises:
        ValueError: If entity type is unknown.
    """
    model_class = ENTITY_MODEL_REGISTRY.get(entity)
    if model_class is None:
        raise ValueError(
            f"Unknown entity type: {entity}. "
            f"Available: {list(ENTITY_MODEL_REGISTRY.keys())}"
        )
    return model_class


def get_parser_for_entity(entity: str) -> ChemblResponseParserImpl[BaseModel]:
    """
    Factory function: return parser for specified entity type.

    Args:
        entity: Entity type name (activity, molecule, target, assay, document).

    Returns:
        Configured ChemblResponseParserImpl for the entity type.

    Raises:
        ValueError: If entity type is unknown.

    Example:
        >>> parser = get_parser_for_entity("molecule")
        >>> records = parser.parse({"molecules": [{"molecule_chembl_id": "CHEMBL1"}]})
    """
    model_class = get_model_for_entity(entity)
    return ChemblResponseParserImpl(model_class)


__all__ = [
    "ChemblEntityType",
    "ENTITY_MODEL_REGISTRY",
    "get_model_for_entity",
    "get_parser_for_entity",
]
