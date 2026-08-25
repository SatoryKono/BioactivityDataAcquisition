"""Public composition contract surface for interface callers.

Modules in this package MUST NOT import ``bioetl.composition.*``.
They may expose Protocol/TypedDict only.
"""

from bioetl.composition.contracts.health import (
    BronzeCleanupServiceProtocol,
    HealthListenerDependenciesProtocol,
    HealthServerDependenciesProtocol,
)
from bioetl.composition.contracts.structural import (
    AuditRequiredFn,
    CandidatePathsFactory,
    ControlPlaneSettingsFn,
    DictHost,
    ModelDumpHost,
    ModelDumpProvider,
    ModelDumpable,
)
from bioetl.composition.contracts.resources import (
    CheckpointRuntimeServiceProtocol,
    CleanupPreviewProtocol,
    CleanupServiceProtocol,
    MedallionLifecycleServiceProtocol,
    QuarantineRuntimeServiceProtocol,
)

__all__ = [
    "AuditRequiredFn",
    "BronzeCleanupServiceProtocol",
    "CandidatePathsFactory",
    "CheckpointRuntimeServiceProtocol",
    "CleanupPreviewProtocol",
    "CleanupServiceProtocol",
    "ControlPlaneSettingsFn",
    "DictHost",
    "HealthListenerDependenciesProtocol",
    "HealthServerDependenciesProtocol",
    "MedallionLifecycleServiceProtocol",
    "ModelDumpHost",
    "ModelDumpProvider",
    "ModelDumpable",

    "QuarantineRuntimeServiceProtocol",
]
