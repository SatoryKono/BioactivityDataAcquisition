"""Domain layer: entities, value objects, ports, and context objects.

This package provides the domain layer public API. Consumers should
import from the specific sub-facades for most symbols:

- ``bioetl.domain.ports``          — Protocol interfaces for DI
- ``bioetl.domain.exceptions``     — Domain-specific error hierarchy
- ``bioetl.domain.value_objects``  — Value objects and DQ report types
- ``bioetl.domain.types``          — Enums, type aliases
- ``bioetl.domain.entities``       — Rich domain objects
- ``bioetl.domain.config``         — Pipeline / runtime config
- ``bioetl.domain.normalization``  — Pure normalization functions
- ``bioetl.domain.transformations``— Pure hashing / DQ functions
- ``bioetl.domain.validation``     — Pure validation functions
- ``bioetl.domain.serialization``  — Centralized JSON helpers
- ``bioetl.domain.composite``      — Composite pipeline models (ADR-026)

Legacy ``bioetl.domain.normalization_*`` modules remain as direct-import
compatibility wrappers only. They are intentionally not exported from the
top-level domain facade; canonical callers should use
``bioetl.domain.normalization``.
"""

from __future__ import annotations

from bioetl.domain import composite, constants, contracts, control_plane, version

# Subpackage registrations (make them importable as bioetl.domain.<name>)
from bioetl.domain import context_cached_bronze
from bioetl.domain import context_filtering
from bioetl.domain import lineage
from bioetl.domain import mapping
from bioetl.domain import observability_contract
from bioetl.domain import registry
from bioetl.domain import types_config_validation

# Events
from bioetl.domain.events import PipelineEvent
from bioetl.domain.version import get_version

__all__ = [
    "PipelineEvent",
    "composite",
    "control_plane",
    "context_cached_bronze",
    "context_filtering",
    "get_version",
    "mapping",
    "registry",
    "version",
    "lineage",
    "observability_contract",
    "types_config_validation",
    # Data contracts (subpackage)
    "contracts",
    # Constants
    "constants",
]
