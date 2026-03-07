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
"""

from __future__ import annotations

from bioetl.domain import composite, constants, contracts, version  # noqa: F401

# Subpackage registrations (make them importable as bioetl.domain.<name>)
from bioetl.domain import context_cached_bronze
from bioetl.domain import context_filtering
from bioetl.domain import mapping  # noqa: F401
from bioetl.domain import normalization_authors
from bioetl.domain import normalization_dates
from bioetl.domain import normalization_pages
from bioetl.domain import observability_contract
from bioetl.domain import registry  # noqa: F401
from bioetl.domain import types_config_validation

# Events
from bioetl.domain.events import PipelineEvent
from bioetl.domain.version import get_version

__all__ = [
    "PipelineEvent",
    "composite",
    "context_cached_bronze",
    "context_filtering",
    "get_version",
    "normalization_authors",
    "normalization_dates",
    "normalization_pages",
    "observability_contract",
    "types_config_validation",
    # Data contracts (subpackage)
    "contracts",
    # Constants
    "constants",
]
