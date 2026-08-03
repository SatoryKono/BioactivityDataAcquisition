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

if TYPE_CHECKING:
    from bioetl.application.services.checkpoint_compatibility_service import (
        CheckpointCompatibilityService,
    )

__all__ = [
    "bootstrap_checkpoint_adapter",
    "bootstrap_checkpoint_compatibility_service",
    "bootstrap_composite_checkpoint_writer",
    "bootstrap_quarantine_adapter",
]


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
    quarantine_path = (
        data_root / "output" / "quarantine"
        if data_root is not None
        else settings.quarantine_path
    )
    quarantine = UnifiedQuarantineAdapter(base_path=str(quarantine_path))
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
    checkpoint_path = (
        data_root / "output" / "checkpoints"
        if data_root is not None
        else settings.checkpoint_path
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
        checkpoint_dir=settings.checkpoint_path / "composite",
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
    from bioetl.application.services.checkpoint_compatibility_service import (
        CheckpointCompatibilityService,
    )

    service = CheckpointCompatibilityService(logger=logger)
    return service
