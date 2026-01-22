"""Bootstrap functions for checkpoint and quarantine CLI operations.

Contains bootstrap functions for checkpoint manager, checkpoint service,
quarantine manager, and quarantine service. Used for CLI inspection
and administrative operations.

Note:
    These functions use NoOp observability since CLI operations don't
    require full runtime observability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint,
    bootstrap_quarantine,
)
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.quarantine_manager import QuarantineManager
    from bioetl.application.services import CheckpointService, QuarantineService

__all__ = [
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
]


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
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.domain.types import RunID

    checkpoint_port = bootstrap_checkpoint(pipeline_name)
    noop_logger = NoOpLogger()

    return CheckpointManager(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()),  # Dummy run_id for CLI inspection
        resume=False,
    )


def bootstrap_checkpoint_service() -> CheckpointService:
    """Bootstrap CheckpointService for CLI administrative operations.

    Creates a CheckpointService for checkpoint listing, deletion, and inspection.
    Uses a generic checkpoint port that can list all pipelines.

    Returns:
        CheckpointService configured for CLI operations.
    """
    from bioetl.application.services import CheckpointService

    settings = get_settings()
    # Use empty pipeline name for global operations
    checkpoint_port = LocalCheckpoint(
        base_path=settings.checkpoint_path,
        pipeline_name="",
    )
    noop_logger = NoOpLogger()

    return CheckpointService(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
    )


def bootstrap_quarantine_service() -> QuarantineService:
    """Bootstrap QuarantineService for CLI administrative operations.

    Creates a QuarantineService for quarantine inspection, replay, and purge.

    Returns:
        QuarantineService configured for CLI operations.
    """
    from bioetl.application.services import QuarantineService

    quarantine_port = bootstrap_quarantine()
    noop_logger = NoOpLogger()

    return QuarantineService(
        quarantine_port=quarantine_port,
        logger=noop_logger,
    )
