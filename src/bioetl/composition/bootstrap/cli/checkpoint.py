"""Bootstrap functions for checkpoint and quarantine CLI operations.

Contains bootstrap functions for checkpoint manager, checkpoint service,
quarantine manager, and quarantine service. Used for CLI inspection
and administrative operations.

Note:
    These functions use NoOp observability since CLI operations don't
    require full runtime observability.
"""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.services.audit_inspection_service import AuditInspectionService
from bioetl.application.services.checkpoint_service import CheckpointService
from bioetl.application.services.observability_workflow_service import (
    ObservabilityWorkflowService,
)
from bioetl.application.services.quarantine_service import QuarantineService
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.admin_runtime_api import (
    CheckpointManagerService,
    QuarantineManagerService,
)
from bioetl.composition.bootstrap.cli.run_manifest import (
    bootstrap_run_manifest_service,
)
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_compatibility_service,
    bootstrap_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.noop import create_noop_metrics
from bioetl.composition.factories.storage._audit import create_audit_port
from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.config import get_settings

__all__ = [
    "bootstrap_audit_inspection_service",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_observability_workflow_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
]


def bootstrap_quarantine_manager(pipeline_name: str) -> QuarantineManagerService:
    """Bootstrap QuarantineManager for CLI inspection operations.

    Creates a QuarantineManager for quarantine inspection and reporting.
    Used by CLI for `quarantine inspect` and similar commands.

    Args:
        pipeline_name: Name of the pipeline to inspect.

    Returns:
        QuarantineManager configured for the specified pipeline.
    """
    quarantine_port = bootstrap_quarantine_port()
    return QuarantineManagerService(
        quarantine_port=quarantine_port,
        pipeline_name=pipeline_name,
    )


def bootstrap_checkpoint_manager(pipeline_name: str) -> CheckpointManagerService:
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
    checkpoint_port = bootstrap_checkpoint_port(pipeline_name)
    noop_logger = create_noop_logger()

    compatibility_service = bootstrap_checkpoint_compatibility_service(noop_logger)

    return CheckpointManagerService(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()),  # Dummy run_id for CLI inspection
        resume=False,
        checkpoint_compatibility_service=compatibility_service,
    )


def bootstrap_checkpoint_service() -> CheckpointService:
    """Bootstrap CheckpointService for CLI administrative operations.

    Creates a CheckpointService for checkpoint listing, deletion, and inspection.
    Uses a generic checkpoint port that can list all pipelines.

    Returns:
        CheckpointService configured for CLI operations.
    """
    settings = get_settings()
    # Use empty pipeline name for global operations
    checkpoint_port = LocalCheckpointAdapter(
        base_path=settings.checkpoint_path,
        pipeline_name="",
    )
    noop_logger = create_noop_logger()

    return CheckpointService(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
    )


def bootstrap_audit_inspection_service() -> AuditInspectionService:
    """Bootstrap AuditInspectionService for operator diagnostics workflows."""
    settings = get_settings()
    noop_logger = create_noop_logger()
    audit_port = create_audit_port(settings=settings, logger=noop_logger)
    return AuditInspectionService(audit_port=audit_port)


def bootstrap_observability_workflow_service() -> ObservabilityWorkflowService:
    """Bootstrap canonical audit/checkpoint diagnostics workflows."""
    checkpoint_service = bootstrap_checkpoint_service()
    audit_service = bootstrap_audit_inspection_service()
    run_manifest_service: RunManifestInspectionService = bootstrap_run_manifest_service()
    return ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )


def bootstrap_quarantine_service() -> QuarantineService:
    """Bootstrap QuarantineService for CLI administrative operations.

    Creates a QuarantineService for quarantine inspection, replay, and purge.

    Returns:
        QuarantineService configured for CLI operations.
    """
    quarantine_port = bootstrap_quarantine_port()
    noop_logger = create_noop_logger()
    noop_metrics = create_noop_metrics()

    return QuarantineService(
        quarantine_port=quarantine_port,
        logger=noop_logger,
        metrics=noop_metrics,
    )
