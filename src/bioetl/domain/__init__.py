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

# Subpackage registrations (make them importable as bioetl.domain.<name>)
from bioetl.domain import mapping  # noqa: F401
from bioetl.domain import registry  # noqa: F401
from bioetl.domain import composite, constants, contracts
from bioetl.domain import version  # noqa: F401

# Events
from bioetl.domain.events import PipelineEvent
from bioetl.domain.version import get_version

__all__ = [
    "PipelineEvent",
    "composite",
    "get_version",
    # Data contracts (subpackage)
    "contracts",
    # Constants
    "constants",
]
