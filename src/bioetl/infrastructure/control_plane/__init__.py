"""Infrastructure control-plane adapters."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.control_plane.artifact_byte_comparison import (
        FileArtifactByteComparisonAdapter,
    )
    from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
        FileControlPlaneArtifactLifecycleStore,
    )
    from bioetl.infrastructure.control_plane.file_contract_registry_store import (
        FileContractRegistryStore,
        RegistryLoadError,
        create_contract_registry,
    )
    from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
        EffectiveConfigArtifactConflictError,
        FileEffectiveConfigArtifactStore,
    )
    from bioetl.infrastructure.control_plane.file_historical_replay_closure_store import (
        FileHistoricalReplayClosureStore,
    )
    from bioetl.infrastructure.control_plane.file_historical_replay_universe_store import (
        FileHistoricalReplayUniverseStore,
    )
    from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
    from bioetl.infrastructure.control_plane.file_run_ledger_store import (
        FileRunLedgerStore,
    )
    from bioetl.infrastructure.control_plane.file_run_manifest_store import (
        FileRunManifestStore,
        RunManifestStoreCorruptionError,
    )
    from bioetl.infrastructure.control_plane.file_workflow_execution_state_store import (
        FileWorkflowExecutionStateStore,
    )
    from bioetl.infrastructure.control_plane.file_workflow_ledger_store import (
        FileWorkflowLedgerStore,
    )
    from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
        FileWorkflowManifestStore,
    )
    from bioetl.infrastructure.control_plane.file_workflow_transform_artifact_store import (
        FileWorkflowTransformArtifactStore,
    )

_CONTRACT_REGISTRY_STORE_MODULE = (
    "bioetl.infrastructure.control_plane.file_contract_registry_store"
)
_EFFECTIVE_CONFIG_ARTIFACT_STORE_MODULE = (
    "bioetl.infrastructure.control_plane.file_effective_config_artifact_store"
)

_EXPORT_MODULES = {
    "EffectiveConfigArtifactConflictError": (
        _EFFECTIVE_CONFIG_ARTIFACT_STORE_MODULE
    ),
    "FileArtifactByteComparisonAdapter": (
        "bioetl.infrastructure.control_plane.artifact_byte_comparison"
    ),
    "FileContractRegistryStore": (
        _CONTRACT_REGISTRY_STORE_MODULE
    ),
    "FileControlPlaneArtifactLifecycleStore": (
        "bioetl.infrastructure.control_plane.file_artifact_lifecycle_store"
    ),
    "FileEffectiveConfigArtifactStore": (
        _EFFECTIVE_CONFIG_ARTIFACT_STORE_MODULE
    ),
    "FileHistoricalReplayClosureStore": (
        "bioetl.infrastructure.control_plane.file_historical_replay_closure_store"
    ),
    "FileHistoricalReplayUniverseStore": (
        "bioetl.infrastructure.control_plane.file_historical_replay_universe_store"
    ),
    "FileLineageStore": "bioetl.infrastructure.control_plane.file_lineage_store",
    "FileRunLedgerStore": ("bioetl.infrastructure.control_plane.file_run_ledger_store"),
    "FileRunManifestStore": (
        "bioetl.infrastructure.control_plane.file_run_manifest_store"
    ),
    "FileWorkflowExecutionStateStore": (
        "bioetl.infrastructure.control_plane.file_workflow_execution_state_store"
    ),
    "FileWorkflowLedgerStore": (
        "bioetl.infrastructure.control_plane.file_workflow_ledger_store"
    ),
    "FileWorkflowManifestStore": (
        "bioetl.infrastructure.control_plane.file_workflow_manifest_store"
    ),
    "FileWorkflowTransformArtifactStore": (
        "bioetl.infrastructure.control_plane.file_workflow_transform_artifact_store"
    ),
    "RegistryLoadError": (
        _CONTRACT_REGISTRY_STORE_MODULE
    ),
    "RunManifestStoreCorruptionError": (
        "bioetl.infrastructure.control_plane.file_run_manifest_store"
    ),
    "create_contract_registry": (
        _CONTRACT_REGISTRY_STORE_MODULE
    ),
}

__all__ = [
    "EffectiveConfigArtifactConflictError",
    "FileArtifactByteComparisonAdapter",
    "FileContractRegistryStore",
    "FileControlPlaneArtifactLifecycleStore",
    "FileEffectiveConfigArtifactStore",
    "FileHistoricalReplayClosureStore",
    "FileHistoricalReplayUniverseStore",
    "FileLineageStore",
    "FileRunLedgerStore",
    "FileRunManifestStore",
    "FileWorkflowExecutionStateStore",
    "FileWorkflowLedgerStore",
    "FileWorkflowManifestStore",
    "FileWorkflowTransformArtifactStore",
    "RegistryLoadError",
    "RunManifestStoreCorruptionError",
    "create_contract_registry",
]


def __getattr__(name: str) -> object:  # pragma: no cover
    """Resolve control-plane adapters lazily for operational startup paths."""
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
