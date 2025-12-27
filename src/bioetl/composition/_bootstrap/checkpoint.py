"""Bootstrap functions for checkpoint and quarantine components.

Contains bootstrap functions for checkpoint service, quarantine service,
and their managers. Used primarily by CLI inspection operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.quarantine_manager import QuarantineManager
    from bioetl.domain.ports import CheckpointPort, QuarantinePort

__all__ = [
    "bootstrap_checkpoint",
    "bootstrap_checkpoint_manager",
    "bootstrap_quarantine",
    "bootstrap_quarantine_manager",
]


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine service for CLI inspection."""
    settings = get_settings()
    base_path = str(settings.silver_path / "common" / "quarantine")
    return UnifiedQuarantine(base_path=base_path)


def bootstrap_checkpoint(pipeline_name: str) -> CheckpointPort:
    """Bootstrap the checkpoint service for CLI inspection."""
    settings = get_settings()
    return LocalCheckpoint(
        base_path=settings.checkpoint_path,
        pipeline_name=pipeline_name,
    )


def bootstrap_quarantine_manager(pipeline_name: str) -> QuarantineManager:
    """Bootstrap QuarantineManager for CLI inspection operations.

    Creates a QuarantineManager for quarantine inspection and reporting.
    Used by CLI for `quarantine inspect` and similar commands.

    Args:
        pipeline_name: Name of the pipeline to inspect.

    Returns:
        QuarantineManager configured for the specified pipeline.
    """
    from bioetl.application.core.quarantine_manager import QuarantineManager

    quarantine_port = bootstrap_quarantine()
    return QuarantineManager(
        quarantine_port=quarantine_port,
        pipeline_name=pipeline_name,
    )


def bootstrap_checkpoint_manager(pipeline_name: str) -> CheckpointManager:
    """Bootstrap CheckpointManager for CLI inspection operations.

    Creates a minimal CheckpointManager for checkpoint listing and inspection.
    Uses NoOpLogger and dummy run_id since CLI operations don't need full
    pipeline execution context.

    Args:
        pipeline_name: Name of the pipeline (used for context, may be ignored
            for operations like list_all).

    Returns:
        CheckpointManager configured for CLI inspection.
    """
    from uuid import uuid4

    from bioetl.application.core.checkpoint_manager import CheckpointManager

    checkpoint_port = bootstrap_checkpoint(pipeline_name)
    noop_logger = NoOpLogger()

    return CheckpointManager(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()),  # Dummy run_id for CLI inspection
        resume=False,
    )
