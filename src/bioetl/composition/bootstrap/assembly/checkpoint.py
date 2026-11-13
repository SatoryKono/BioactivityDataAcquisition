"""Bootstrap functions for checkpoint and quarantine ports.

Provides basic port creation for checkpoint and quarantine infrastructure.
These are low-level building blocks used by both CLI and runtime.

Note:
    Higher-level runtime services and administration services are created in cli/ module
    since they require additional context (pipeline_name, run_id, etc.)
    and use NoOp observability for CLI operations.
"""

from __future__ import annotations

from pathlib import Path
from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.application.services.run_reports.paths import resolve_report_root
from bioetl.domain.ports import MetricsPort, RawRunManifestInspectionPort
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContext,
    _SelectedRootLedgerPort,
)


from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import (
    CheckpointPort,
    CompositeCheckpointPort,
    LoggerPort,
    QuarantinePort,
)
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)

from bioetl.application.services.checkpoint.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)

if TYPE_CHECKING:
    from bioetl.application.services.checkpoint.checkpoint_compatibility_service import (
        CheckpointCompatibilityService,
    )

__all__ = [
    "bind_selected_evidence_validation",
    "bootstrap_checkpoint_adapter",
    "bootstrap_checkpoint_compatibility_service",
    "bootstrap_composite_checkpoint_writer",
    "bootstrap_quarantine_adapter",
]


def _logical_fs_path(path: Path) -> Path:
    """Keep POSIX-absolute roots logical; do not pin them to a Windows drive.

    ``Path('/custom/x').resolve()`` on Windows becomes ``C:\\custom\\x``.
    Tests and operator-supplied POSIX roots must stay comparable as POSIX.
    """
    candidate = Path(path)
    posix_text = candidate.as_posix()
    if posix_text.startswith("/") and not candidate.drive:
        return Path(posix_text)
    return candidate


def bootstrap_quarantine_adapter(*, data_root: Path | None = None) -> QuarantinePort:
    """Create a quarantine port implementation for record quarantine storage.

    Creates a UnifiedQuarantineAdapter adapter using centralized quarantine_path
    from settings (data_dir/quarantine) for unified quarantine storage
    independent of entity paths.

    Layer: Returns domain port implementation (QuarantinePort).

    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    settings = get_settings()
    quarantine_path = _logical_fs_path(
        data_root / "output" / "quarantine"
        if data_root is not None
        else Path(settings.quarantine_path)
    )
    quarantine = UnifiedQuarantineAdapter(base_path=quarantine_path.as_posix())
    assert isinstance(quarantine, QuarantinePort), (
        f"UnifiedQuarantineAdapter must implement QuarantinePort, got {type(quarantine)}"
    )
    return quarantine


def bootstrap_checkpoint_adapter(
    pipeline_name: str,
    *,
    data_root: Path | None = None,
) -> CheckpointPort:
    """Create a checkpoint port implementation for pipeline state persistence.

    Creates a LocalCheckpointAdapter adapter for the specified pipeline using
    the checkpoint_path from settings.

    Layer: Returns domain port implementation (CheckpointPort).

    Args:
        pipeline_name: Name of the pipeline for checkpoint scoping.

    Returns:
        CheckpointPort implementation for checkpoint operations.
    """
    settings = get_settings()
    checkpoint_path = _logical_fs_path(
        data_root / "output" / "checkpoints"
        if data_root is not None
        else Path(settings.checkpoint_path)
    )
    checkpoint = LocalCheckpointAdapter(
        base_path=checkpoint_path,
        pipeline_name=pipeline_name,
    )
    assert isinstance(checkpoint, CheckpointPort), (
        f"LocalCheckpointAdapter must implement CheckpointPort, got {type(checkpoint)}"
    )
    return checkpoint


def bootstrap_composite_checkpoint_writer() -> CompositeCheckpointPort:
    """Create a composite checkpoint port implementation for runtime resume state.

    Composite checkpoints live under the canonical checkpoint root with a
    dedicated ``composite/`` subdirectory so runtime and operational tooling
    share one consistent storage layout.

    Returns:
        CompositeCheckpointPort implementation for composite checkpoint operations.
    """
    settings = get_settings()
    checkpoint = FileCompositeCheckpointWriter(
        checkpoint_dir=_logical_fs_path(Path(settings.checkpoint_path) / "composite"),
        history_root=_logical_fs_path(Path(settings.checkpoint_path)),
    )
    assert isinstance(checkpoint, CompositeCheckpointPort), (
        "FileCompositeCheckpointWriter must implement CompositeCheckpointPort, "
        f"got {type(checkpoint)}"
    )
    return checkpoint


def bootstrap_checkpoint_compatibility_service(
    logger: LoggerPort,
) -> CheckpointCompatibilityService:
    """Create checkpoint compatibility service for DQ contract validation.

    Creates a CheckpointCompatibilityService for validating checkpoint compatibility
    based on Data Quality contract hashes and pipeline versions.

    Args:
        logger: Logger instance for observability.

    Returns:
        CheckpointCompatibilityService instance.
    """

    service = CheckpointCompatibilityService(logger=logger)
    return service


def bind_selected_evidence_validation(
    context: FileEvidenceReadContext,
    *,
    archive_root: Path | None,
    report_root: Path | None,
    metrics: MetricsPort | None,
) -> FileEvidenceReadContext:
    """Compose validation ports on the same selected root as persisted status capture."""
    output_root = context.data_root / "output" / "control"
    if archive_root is not None:
        report_root = resolve_report_root(root=report_root)
        archive_verifier: FileArchiveStore | None = FileArchiveStore(
            context.data_root, archive_root, report_root
        )
    else:
        archive_verifier = None
    if isinstance(context.manifest_port, RawRunManifestInspectionPort):
        manifest_inspector: RawRunManifestInspectionPort | None = context.manifest_port
    else:
        manifest_inspector = None
    validation_service = ControlPlaneEvidenceService(
        ledger_port=_SelectedRootLedgerPort(context),
        lineage_store=context.lineage_port,
        manifest_inspector=manifest_inspector,
        lifecycle_planner=FileControlPlaneArtifactLifecycleStore(
            base_path=output_root, metrics=metrics
        ),
        archive_verifier=archive_verifier,
    )
    return FileEvidenceReadContext(
        data_root=context.data_root,
        trusted_alias_base=context.trusted_alias_base,
        manifest_port=context.manifest_port,
        ledger_port=context.ledger_port,
        workflow_manifest_port=context.workflow_manifest_port,
        lineage_port=context.lineage_port,
        replay_object_verifier=context.replay_object_verifier,
        validation_service=validation_service,
    )
