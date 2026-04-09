"""Composition services for cross-cutting concerns.

Services in the composition layer coordinate between layers and build
complex objects. Unlike application services, these do not contain
business logic but rather assemble components.

Services:
- MetadataCoordinator: Centralized metadata creation for Medallion layers
- Versioning utilities: Git commit, config hash, pipeline version
"""

from __future__ import annotations

from bioetl.composition._services import MetadataCoordinator
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)

# Re-export input types from domain.ports for convenience
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinator",
    "SilverMetadataInput",
    "compute_config_hash",
    "get_git_commit",
    "get_pipeline_version",
]
