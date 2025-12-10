"""
Constants for ChEMBL API client.

This module contains mappings and constants used across ChEMBL client implementations.
"""

from types import MappingProxyType
from typing import Mapping

# Entity to endpoint mapping for ChEMBL API.
#
# ChEMBL API uses different endpoint names than our domain entity names in some cases.
# This mapping translates our internal entity names to ChEMBL API endpoint names.
#
# Mapping rationale:
#   - "activity" → "activity": Direct mapping, no translation needed.
#   - "assay" → "assay": Direct mapping, no translation needed.
#   - "target" → "target": Direct mapping, no translation needed.
#   - "molecule" → "molecule": Direct mapping, no translation needed.
#   - "publication" → "document": ChEMBL API uses "document" endpoint for publications.
#     The ChEMBL database stores publication data (journal articles, patents, etc.)
#     in the "document" table, hence the API endpoint is named "document".
#     Our domain model uses "publication" as it better represents the concept.
#
# Reference: https://www.ebi.ac.uk/chembl/api/data/docs
ENTITY_ENDPOINT_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "activity": "activity",
        "assay": "assay",
        "target": "target",
        "molecule": "molecule",
        "publication": "document",
    }
)

# Set of supported entity names for validation
SUPPORTED_ENTITIES: frozenset[str] = frozenset(ENTITY_ENDPOINT_ALIASES.keys())


def resolve_endpoint(entity: str) -> str:
    """
    Resolve entity name to ChEMBL API endpoint.

    Args:
        entity: The domain entity name (e.g., "publication", "activity").

    Returns:
        The corresponding ChEMBL API endpoint name.

    Raises:
        ValueError: If the entity is not supported.
    """
    if entity not in ENTITY_ENDPOINT_ALIASES:
        raise ValueError(f"Unknown entity: {entity}")
    return ENTITY_ENDPOINT_ALIASES[entity]


__all__ = [
    "ENTITY_ENDPOINT_ALIASES",
    "SUPPORTED_ENTITIES",
    "resolve_endpoint",
]
