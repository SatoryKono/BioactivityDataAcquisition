"""Composition services for cross-cutting concerns.

Services in the composition layer coordinate between layers and build
complex objects. Unlike application services, these do not contain
business logic but rather assemble components.

Services:
- MetadataCoordinator: Centralized metadata creation for Medallion layers
"""

from bioetl.composition.services.metadata_coordinator import MetadataCoordinator

# Re-export input types from domain.ports for convenience
from bioetl.domain.ports.metadata_coordinator import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinator",
    "SilverMetadataInput",
]
