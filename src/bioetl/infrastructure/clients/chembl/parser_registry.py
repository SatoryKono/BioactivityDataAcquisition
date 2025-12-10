"""Registry for ChEMBL entity parsers (infrastructure layer).

This module provides generic parsing capabilities without domain model knowledge.
Domain model mapping happens in application layer
(bioetl.application.mappers.chembl.model_registry).
"""

from __future__ import annotations

from typing import Literal, TypeAlias

from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)

ChemblEntityType: TypeAlias = Literal[
    "activity", "molecule", "target", "assay", "document"
]

# Supported entities (without model references)
SUPPORTED_ENTITIES: frozenset[str] = frozenset(
    {"activity", "molecule", "target", "assay", "document"}
)


def get_parser_for_entity(entity: str) -> ResponseParserPortABC:
    """Get generic parser for entity type.

    Note: All entities use the same generic parser in infrastructure.
    Domain model mapping happens in application layer.

    Args:
        entity: Entity type name.

    Returns:
        Generic response parser.

    Raises:
        ValueError: If entity type is not supported.

    Example:
        >>> parser = get_parser_for_entity("molecule")
        >>> records = parser.parse_to_records({"molecules": [{"id": "1"}]})
    """
    if entity not in SUPPORTED_ENTITIES:
        raise ValueError(
            f"Unknown entity type: {entity}. "
            f"Supported: {sorted(SUPPORTED_ENTITIES)}"
        )
    return ChemblGenericResponseParser()


def is_supported_entity(entity: str) -> bool:
    """Check if entity type is supported.

    Args:
        entity: Entity type name to check.

    Returns:
        True if entity type is supported, False otherwise.
    """
    return entity in SUPPORTED_ENTITIES


__all__ = [
    "ChemblEntityType",
    "SUPPORTED_ENTITIES",
    "get_parser_for_entity",
    "is_supported_entity",
]
