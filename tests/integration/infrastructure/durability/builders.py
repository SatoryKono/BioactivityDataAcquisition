"""Assemble each concrete store from the S1 durability denominator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
)
from bioetl.infrastructure.control_plane.file_contract_registry_store import (
    FileContractRegistryStore,
)
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.control_plane.file_historical_replay_closure_store import (
    FileHistoricalReplayClosureStore,
)
from bioetl.infrastructure.control_plane.file_historical_replay_universe_store import (
    FileHistoricalReplayUniverseStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
)
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
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
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.time.system_clock import SystemClock
from bioetl.infrastructure.validation import ContractAwareSilverValidator

from tests.integration.infrastructure.durability.data_factories import (
    RUN_REPORT_MARKER,
    STORE_NAMES,
)


@dataclass(frozen=True, slots=True)
class DurabilityCollaborators:
    """Explicit runtime objects shared by construction smoke."""

    logger: NoOpLogger
    metrics: NoOpMetrics
    clock: SystemClock
    silver_validator: ContractAwareSilverValidator


@dataclass(frozen=True, slots=True)
class StoreAssembly:
    """One constructed store and the paths that must stay under its root."""

    name: str
    instance: object
    expected_type: type[object]
    anchored_paths: tuple[Path, ...]
    bound_metrics: object | None = None
    bound_validator: object | None = None
    bound_clock: object | None = None


def isolated_store_root(tmp_path: Path, store_name: str) -> Path:
    """Create the directory that owns one store assembly."""
    root = tmp_path / store_name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(value: Path | str) -> Path:
    return Path(value)


def _read_attr(instance: object, name: str) -> object:
    return getattr(instance, name)


def _assembly(
    name: str,
    expected_type: type[object],
    instance: object,
    *anchored_paths: Path | str,
    bound_metrics: object | None = None,
    bound_validator: object | None = None,
    bound_clock: object | None = None,
) -> StoreAssembly:
    if type(instance) is not expected_type:
        raise RuntimeError(
            f"{name} assembled {type(instance).__name__}, expected {expected_type.__name__}"
        )
    return StoreAssembly(
        name=name,
        instance=instance,
        expected_type=expected_type,
        anchored_paths=tuple(_path(path) for path in anchored_paths),
        bound_metrics=bound_metrics,
        bound_validator=bound_validator,
        bound_clock=bound_clock,
    )


def _bronze(root: Path, deps: DurabilityCollaborators) -> StoreAssembly:
    writer = BronzeWriter(root, deps.logger, deps.metrics)
    return _assembly(
        "g1_bronze",
        BronzeWriter,
        writer,
        writer.base_path,
        bound_metrics=writer._metrics,
    )


def _silver(root: Path, deps: DurabilityCollaborators) -> StoreAssembly:
    writer = SilverWriter(
        root,
        deps.logger,
        runtime_request=SilverWriterRuntimeServicesRequest(
            clock=deps.clock,
            logger=deps.logger,
            metrics=deps.metrics,
            silver_validator=deps.silver_validator,
        ),
    )
    return _assembly(
        "g1_silver",
        SilverWriter,
        writer,
        writer.base_path,
        bound_validator=_read_attr(writer, "_silver_validator"),
        bound_clock=writer._clock,
    )


def _gold(root: Path, deps: DurabilityCollaborators) -> StoreAssembly:
    writer = GoldWriter(root, deps.logger)
    return _assembly("g1_gold", GoldWriter, writer, writer.base_path)


def _quarantine(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    adapter = UnifiedQuarantineAdapter(str(root))
    return _assembly(
        "g2_quarantine", UnifiedQuarantineAdapter, adapter, adapter.base_path
    )


def _checkpoint(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    adapter = LocalCheckpointAdapter(root)
    return _assembly(
        "g2_checkpoint", LocalCheckpointAdapter, adapter, adapter.base_path
    )


def _run_manifest(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileRunManifestStore(root)
    return _assembly("g3_run_manifest", FileRunManifestStore, store, store.base_path)


def _run_ledger(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileRunLedgerStore(root)
    return _assembly("g3_run_ledger", FileRunLedgerStore, store, store.base_path)


def _lineage(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileLineageStore(root)
    return _assembly("g3_lineage", FileLineageStore, store, store.base_path)


def _workflow_state(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileWorkflowExecutionStateStore(root)
    return _assembly(
        "g4_workflow_execution_state",
        FileWorkflowExecutionStateStore,
        store,
        store.base_path,
    )


def _workflow_manifest(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileWorkflowManifestStore(root)
    return _assembly(
        "g4_workflow_manifest",
        FileWorkflowManifestStore,
        store,
        store.base_path,
    )


def _workflow_ledger(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileWorkflowLedgerStore(root)
    return _assembly(
        "g4_workflow_ledger",
        FileWorkflowLedgerStore,
        store,
        store.base_path,
    )


def _workflow_transform(root: Path, deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileWorkflowTransformArtifactStore(root, deps.clock)
    return _assembly(
        "g4_workflow_transform_artifact",
        FileWorkflowTransformArtifactStore,
        store,
        store.base_path,
        bound_clock=store.clock,
    )


def _effective_config(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileEffectiveConfigArtifactStore(root)
    return _assembly(
        "g5_effective_config",
        FileEffectiveConfigArtifactStore,
        store,
        store.base_path,
    )


def _contract_registry(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    registry_path = root / "registry.json"
    store = FileContractRegistryStore(registry_path)
    return _assembly(
        "g5_contract_registry",
        FileContractRegistryStore,
        store,
        store.registry_path,
    )


def _replay_universe(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileHistoricalReplayUniverseStore(root)
    return _assembly(
        "g5_historical_replay_universe",
        FileHistoricalReplayUniverseStore,
        store,
        store.base_path,
    )


def _replay_closure(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileHistoricalReplayClosureStore(root)
    return _assembly(
        "g5_historical_replay_closure",
        FileHistoricalReplayClosureStore,
        store,
        store.base_path,
    )


def _archive(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    data_root = root / "data"
    archive_root = root / "archive"
    data_root.mkdir()
    archive_root.mkdir()
    store = FileArchiveStore(data_root, archive_root)
    return _assembly(
        "g5_archive",
        FileArchiveStore,
        store,
        store.data_root,
        store.archive_root,
    )


def _lifecycle(root: Path, deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileControlPlaneArtifactLifecycleStore(root, deps.logger, deps.metrics)
    return _assembly(
        "g5_artifact_lifecycle",
        FileControlPlaneArtifactLifecycleStore,
        store,
        store.base_path,
    )


def _contract_evidence(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileContractEvidenceRecorder(root)
    return _assembly(
        "g5_contract_evidence",
        FileContractEvidenceRecorder,
        store,
        store.base_path,
    )


def _provider_health(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    store = FileProviderHealthEvidenceStore(root)
    return _assembly(
        "g5_provider_health",
        FileProviderHealthEvidenceStore,
        store,
        store.base_path,
    )


def _run_report(root: Path, _deps: DurabilityCollaborators) -> StoreAssembly:
    adapter = FileRunReportStoreAdapter()
    marker = root / "marker.txt"
    adapter.write_text(str(marker), RUN_REPORT_MARKER)
    return _assembly("g5_run_report", FileRunReportStoreAdapter, adapter, marker)


_BUILDERS: dict[str, Callable[[Path, DurabilityCollaborators], StoreAssembly]] = {
    "g1_bronze": _bronze,
    "g1_silver": _silver,
    "g1_gold": _gold,
    "g2_quarantine": _quarantine,
    "g2_checkpoint": _checkpoint,
    "g3_run_manifest": _run_manifest,
    "g3_run_ledger": _run_ledger,
    "g3_lineage": _lineage,
    "g4_workflow_execution_state": _workflow_state,
    "g4_workflow_manifest": _workflow_manifest,
    "g4_workflow_ledger": _workflow_ledger,
    "g4_workflow_transform_artifact": _workflow_transform,
    "g5_effective_config": _effective_config,
    "g5_contract_registry": _contract_registry,
    "g5_historical_replay_universe": _replay_universe,
    "g5_historical_replay_closure": _replay_closure,
    "g5_archive": _archive,
    "g5_artifact_lifecycle": _lifecycle,
    "g5_contract_evidence": _contract_evidence,
    "g5_provider_health": _provider_health,
    "g5_run_report": _run_report,
}


def builder_names() -> tuple[str, ...]:
    """Return store names in the same order as the committed denominator."""
    return tuple(_BUILDERS)


def assemble_store(
    store_name: str,
    root: Path,
    deps: DurabilityCollaborators,
) -> StoreAssembly:
    """Build one named store and keep its files under ``root``."""
    if store_name not in STORE_NAMES:
        raise KeyError(f"unknown durability store {store_name}")
    assembly = _BUILDERS[store_name](root, deps)
    if assembly.name != store_name:
        raise RuntimeError(f"builder returned {assembly.name} for {store_name}")
    return assembly
