"""Workflow transform registry assembly (extracted from _workflow_services)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.builtins import (
    register_builtin_workflow_transforms,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import (
    StorageRowReconciliationAdapter,
)
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.control_plane import FileWorkflowTransformArtifactStore


def _workflow_reconciliation_loggers() -> tuple[LoggerPort, LoggerPort]:
    """Return FK and row reconciliation loggers for workflow transforms."""
    root = bootstrap_logger("workflow_reconciliation").bind(
        component="workflow_reconciliation",
    )
    return (
        root.bind(adapter="SilverForeignKeyReconciliationAdapter"),
        root.bind(adapter="StorageRowReconciliationAdapter"),
    )


def build_workflow_transform_registry(
    settings: Settings,
    metrics: MetricsPort,
    artifact_sink: FileWorkflowTransformArtifactStore | None = None,
) -> WorkflowTransformRegistry:
    """Assemble workflow transform storage and builtin transform registry."""
    workflow_storage_logger = create_noop_logger()
    transform_storage = SilverWriter(
        base_path=settings.silver_path,
        logger=workflow_storage_logger,
        runtime_services=build_silver_writer_runtime_services(
            SilverWriterRuntimeServicesRequest(
                csv_exporter=None,
                tracing=NoOpTracing(),
                write_policy=None,
                metrics=metrics,
                audit=NoOpAudit(),
                logger=workflow_storage_logger,
                silver_validator=NoOpValidator(),
                metadata_writer=NoOpMetadataWriter(),
                metadata_coordinator=None,
                lineage_store=None,
                dq_calculator=None,
                merge_resilience_policy=None,
                base_path=settings.silver_path,
                pipeline_name="workflow_transforms",
            )
        ),
        pipeline_name="workflow_transforms",
    )
    transform_gold_storage = GoldWriter(
        base_path=settings.gold_path,
        logger=create_noop_logger(),
        runtime_services=GoldWriterRuntimeServices(
            csv_exporter=None,
            tracing=NoOpTracing(),
            metrics=metrics,
            audit=NoOpAudit(),
            metadata_writer=NoOpMetadataWriter(),
            metadata_coordinator=None,
            lineage_store=None,
        ),
    )
    foreign_key_reconciliation_logger, row_reconciliation_logger = (
        _workflow_reconciliation_loggers()
    )
    reconciliation_quarantine = UnifiedQuarantineAdapter(
        base_path=str(settings.quarantine_path),
    )
    return register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=transform_storage,
            logger=foreign_key_reconciliation_logger,
            clock=SystemClock(),
            metrics=metrics,
            quarantine=reconciliation_quarantine,
            quarantine_pipeline_name="workflow_transforms",
            gold_writer=transform_gold_storage,
            artifact_sink=artifact_sink,
        ),
        row_reconciliation_port=StorageRowReconciliationAdapter(
            silver_reader=transform_storage,
            gold_reader=transform_gold_storage,
            logger=row_reconciliation_logger,
            metrics=metrics,
        ),
    )
