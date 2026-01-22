"""Bootstrap functions for checkpoint and quarantine ports.

Provides basic port creation for checkpoint and quarantine infrastructure.
These are low-level building blocks used by both CLI and runtime.

Note:
    Higher-level managers and services are created in cli/ module
    since they require additional context (pipeline_name, run_id, etc.)
    and use NoOp observability for CLI operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from bioetl.domain.ports import CheckpointPort, QuarantinePort

__all__ = [
    "bootstrap_checkpoint",
    "bootstrap_quarantine",
]


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine port for record quarantine storage.

    Creates a UnifiedQuarantine adapter using centralized quarantine_path
    from settings (data_dir/quarantine) for unified quarantine storage
    independent of entity paths.

    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    settings = get_settings()
    return UnifiedQuarantine(base_path=str(settings.quarantine_path))


def bootstrap_checkpoint(pipeline_name: str) -> CheckpointPort:
    """Bootstrap the checkpoint port for pipeline state persistence.

    Creates a LocalCheckpoint adapter for the specified pipeline using
    the checkpoint_path from settings.

    Args:
        pipeline_name: Name of the pipeline for checkpoint scoping.

    Returns:
        CheckpointPort implementation for checkpoint operations.
    """
    settings = get_settings()
    return LocalCheckpoint(
        base_path=settings.checkpoint_path,
        pipeline_name=pipeline_name,
    )
