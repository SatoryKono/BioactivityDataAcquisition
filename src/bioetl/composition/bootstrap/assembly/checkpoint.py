"""Bootstrap functions for checkpoint and quarantine ports.

Provides basic port creation for checkpoint and quarantine infrastructure.
These are low-level building blocks used by both CLI and runtime.

Note:
    Higher-level managers and services are created in cli/ module
    since they require additional context (pipeline_name, run_id, etc.)
    and use NoOp observability for CLI operations.
"""

from __future__ import annotations

from bioetl.domain.ports import CheckpointPort, QuarantinePort
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter

__all__ = [
    # Deprecated aliases (backward compatibility)
    "bootstrap_checkpoint",
    # Canonical names (use these)
    "bootstrap_checkpoint_port",
    "bootstrap_quarantine",
    "bootstrap_quarantine_port",
]


def bootstrap_quarantine_port() -> QuarantinePort:
    """Create a quarantine port implementation for record quarantine storage.

    Creates a UnifiedQuarantineAdapter adapter using centralized quarantine_path
    from settings (data_dir/quarantine) for unified quarantine storage
    independent of entity paths.

    Layer: Returns domain port implementation (QuarantinePort).

    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    settings = get_settings()
    quarantine = UnifiedQuarantineAdapter(base_path=str(settings.quarantine_path))
    assert isinstance(quarantine, QuarantinePort), (
        f"UnifiedQuarantineAdapter must implement QuarantinePort, got {type(quarantine)}"
    )
    return quarantine


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine port for record quarantine storage.


    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    return bootstrap_quarantine_port()


def bootstrap_checkpoint_port(pipeline_name: str) -> CheckpointPort:
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
    checkpoint = LocalCheckpointAdapter(
        base_path=settings.checkpoint_path,
        pipeline_name=pipeline_name,
    )
    assert isinstance(checkpoint, CheckpointPort), (
        f"LocalCheckpointAdapter must implement CheckpointPort, got {type(checkpoint)}"
    )
    return checkpoint


def bootstrap_checkpoint(pipeline_name: str) -> CheckpointPort:
    """Bootstrap the checkpoint port for pipeline state persistence.


    Args:
        pipeline_name: Name of the pipeline for checkpoint scoping.

    Returns:
        CheckpointPort implementation for checkpoint operations.
    """
    return bootstrap_checkpoint_port(pipeline_name=pipeline_name)
