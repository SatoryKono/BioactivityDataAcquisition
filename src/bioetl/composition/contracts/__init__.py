"""Public composition contract surface for interface callers.

Modules in this package MUST NOT import ``bioetl.composition.*``.
They may expose Protocol/TypedDict only.
"""

from bioetl.composition.contracts.health import (
    BronzeCleanupServiceProtocol,
    HealthServerDependenciesProtocol,
)
from bioetl.composition.contracts.resources import (
    CheckpointRuntimeServiceProtocol,
    CleanupPreviewProtocol,
    CleanupServiceProtocol,
    MedallionLifecycleServiceProtocol,
    QuarantineRuntimeServiceProtocol,
)

__all__ = [
    "BronzeCleanupServiceProtocol",
    "CheckpointRuntimeServiceProtocol",
    "CleanupPreviewProtocol",
    "CleanupServiceProtocol",
    "HealthServerDependenciesProtocol",
    "MedallionLifecycleServiceProtocol",
    "QuarantineRuntimeServiceProtocol",
]
