# basedpyright residual burn-down (shrink-only product surface).
"""Workflow-specific composition service assembly helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast, TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.composition.occurrence_identity import (
    create_runtime_occurrence_id,
    create_runtime_occurrence_run_id,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.workflow.execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow.inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.application.services.control_plane.workflow.ledger_service import (
        WorkflowLedgerService,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.workflow.workflow_runner_service import (
        WorkflowRunnerService,
    )
    from bioetl.application.services.workflow.workflow_transform_artifacts import (
        WorkflowTransformArtifactSinkProtocol,
    )
    from bioetl.application.workflow.transforms import WorkflowTransformRegistry
    from bioetl.domain.control_plane import WorkflowManifest
    from bioetl.domain.ports import LockPort, MetricsPort, WorkflowLedgerPort
    from bioetl.domain.workflow import WorkflowConfig
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "load_workflow_config",
]

_workflow_memory_lock: LockPort | None = None


@runtime_checkable
class _WorkflowMetricsFactory(Protocol):
    """Lazy metrics-factory contract for canonical workflow settings."""

    def __call__(self, settings: Settings, /) -> MetricsPort: ...


def _create_workflow_metrics(settings: Settings) -> MetricsPort:
    """Resolve the patchable metrics factory through a typed lazy boundary."""
    from bioetl.composition.factories.services.port_factories import create_metrics

    candidate: object = create_metrics
    if not isinstance(candidate, _WorkflowMetricsFactory):
        raise TypeError("Workflow metrics factory does not satisfy its contract")
    return candidate(settings)


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical composition service seam."""
    from bioetl.infrastructure.config.workflow_config_api import (
        load_workflow_config as load_workflow_config_impl,
    )

    return load_workflow_config_impl(name, configs_root=resolve_configs_root())


def _default_pipeline_runner_service_factory(
    registry: PipelineRegistry | None,
) -> PipelineRunnerService:
    """Build the pipeline runner service without depending on the facade module."""
    from bioetl.composition.bootstrap.runtime.runner import (
        bootstrap_pipeline_runner_service,
    )

    return bootstrap_pipeline_runner_service(registry=registry)


def _build_workflow_transform_registry(
    settings: Settings,
    metrics: MetricsPort,
    artifact_sink: WorkflowTransformArtifactSinkProtocol | None = None,
) -> WorkflowTransformRegistry:
    """Assemble workflow transform storage and builtin transform registry."""
    from bioetl.application.workflow.transforms import WorkflowTransformRegistry
    from bioetl.application.workflow.transforms.builtins import (
        register_builtin_workflow_transforms,
    )
    from bioetl.composition.bootstrap.runtime.observability import (
        bootstrap_logger,
    )
    from bioetl.composition.bootstrap.cli.noop import create_noop_logger
    from bioetl.domain.ports.noop import NoOpAudit, NoOpMetadataWriter, NoOpTracing
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
                silver_validator=None,
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
    reconciliation_logger = bootstrap_logger("workflow_reconciliation").bind(
        component="workflow_reconciliation",
    )
    foreign_key_reconciliation_logger = reconciliation_logger.bind(
        adapter="SilverForeignKeyReconciliationAdapter",
    )
    row_reconciliation_logger = reconciliation_logger.bind(
        adapter="StorageRowReconciliationAdapter",
    )
    reconciliation_quarantine = UnifiedQuarantineAdapter(
        base_path=str(settings.quarantine_path),
    )
    return register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=transform_storage,
            logger=foreign_key_reconciliation_logger,
            metrics=metrics,
            quarantine=reconciliation_quarantine,
            quarantine_pipeline_name="workflow_transforms",
            gold_writer=transform_gold_storage,
            artifact_sink=cast(Any, artifact_sink),
        ),
        row_reconciliation_port=StorageRowReconciliationAdapter(
            silver_reader=transform_storage,
            gold_reader=transform_gold_storage,
            logger=row_reconciliation_logger,
            metrics=metrics,
        ),
    )


def get_workflow_runner_service(
    registry: PipelineRegistry | None = None,
    *,
    pipeline_runner_service_factory: Callable[
        [PipelineRegistry | None], PipelineRunnerService
    ]
    | None = None,
) -> WorkflowRunnerService:
    """Build the baseline declarative workflow runner through composition seams."""
    from bioetl.application.services.workflow.workflow_runner_service import (
        WorkflowRunnerService,
    )
    from bioetl.application.services.workflow.workflow_transform_service import (
        WorkflowTransformService,
    )
    from bioetl.infrastructure.control_plane import FileWorkflowTransformArtifactStore
    from bioetl.infrastructure.time import SystemClock

    settings = get_settings()
    metrics = _create_workflow_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    artifact_sink = FileWorkflowTransformArtifactStore(
        base_path=output_root / "workflow_transform_results",
        clock=SystemClock(),
    )
    transform_registry = _build_workflow_transform_registry(
        settings,
        metrics,
        artifact_sink=artifact_sink,
    )
    pipeline_runner_factory = (
        _default_pipeline_runner_service_factory
        if pipeline_runner_service_factory is None
        else pipeline_runner_service_factory
    )
    return WorkflowRunnerService(
        pipeline_runner=pipeline_runner_factory(registry),
        transform_service=WorkflowTransformService(
            registry=transform_registry,
            metrics=metrics,
        ),
        metrics=metrics,
        workflow_transform_artifact_sink=artifact_sink,
    )


def _get_workflow_memory_lock() -> LockPort:
    global _workflow_memory_lock
    if _workflow_memory_lock is None:
        from bioetl.infrastructure.locking import MemoryLock

        _workflow_memory_lock = MemoryLock()
    return _workflow_memory_lock


def _create_workflow_ledger_service(
    ledger_port: WorkflowLedgerPort,
    manifest: WorkflowManifest,
) -> WorkflowLedgerService:
    from bioetl.application.services.control_plane.workflow.ledger_service import (
        WorkflowLedgerService,
    )

    return WorkflowLedgerService(
        ledger_port=ledger_port,
        manifest_id=manifest.manifest_id,
        workflow_run_id=manifest.workflow_run_id,
        workflow_name=manifest.workflow_name,
        _entry_id_factory=lambda: create_runtime_occurrence_id("workflow_ledger_entry"),
    )


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
    workflow_lock_port: LockPort | None = None,
) -> WorkflowExecutionService:
    """Build workflow execution orchestration with durable control-plane seams."""
    from bioetl.application.services.control_plane.workflow.execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow.manifest_service import (
        WorkflowManifestService,
    )
    from bioetl.infrastructure.control_plane import (
        FileWorkflowExecutionStateStore,
        FileWorkflowLedgerStore,
        FileWorkflowManifestStore,
    )
    from bioetl.infrastructure.time import SystemClock

    settings = get_settings()
    metrics = _create_workflow_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    manifest_store = FileWorkflowManifestStore(
        base_path=output_root / "workflow_manifest",
        metrics=metrics,
    )
    ledger_store = FileWorkflowLedgerStore(
        base_path=output_root / "workflow_ledger",
        metrics=metrics,
    )
    state_store = FileWorkflowExecutionStateStore(
        base_path=output_root / "workflow_state",
        metrics=metrics,
    )
    return WorkflowExecutionService(
        workflow_runner=get_workflow_runner_service(registry=registry),
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_store,
            clock=SystemClock(),
            _manifest_id_factory=lambda: create_runtime_occurrence_id(
                "workflow_manifest"
            ),
        ),
        workflow_ledger_port=ledger_store,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_store,
        workflow_lock_port=workflow_lock_port
        if workflow_lock_port is not None
        else _get_workflow_memory_lock(),
        run_id_factory=lambda: create_runtime_occurrence_run_id("workflow_execution"),
    )


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Get workflow inspection service for operator diagnostics."""
    from bioetl.application.services.control_plane.workflow.inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.infrastructure.control_plane import (
        FileWorkflowExecutionStateStore,
        FileWorkflowLedgerStore,
        FileWorkflowManifestStore,
    )

    settings = get_settings()
    metrics = _create_workflow_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return WorkflowInspectionService(
        manifest_port=FileWorkflowManifestStore(
            base_path=output_root / "workflow_manifest",
            metrics=metrics,
        ),
        ledger_port=FileWorkflowLedgerStore(
            base_path=output_root / "workflow_ledger",
            metrics=metrics,
        ),
        state_port=FileWorkflowExecutionStateStore(
            base_path=output_root / "workflow_state",
            metrics=metrics,
        ),
    )
