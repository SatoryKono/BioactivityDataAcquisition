"""Workflow-specific composition service assembly helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import get_settings

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
    from bioetl.application.services.workflow_runner_service import (
        WorkflowRunnerService,
    )
    from bioetl.domain.control_plane import WorkflowManifest
    from bioetl.domain.ports import LockPort, WorkflowLedgerPort
    from bioetl.domain.workflow import WorkflowConfig

__all__ = [
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "load_workflow_config",
]

_WORKFLOW_MEMORY_LOCK: object | None = None


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical composition service seam."""
    from bioetl.infrastructure.config.workflow_config_api import (
        load_workflow_config as load_workflow_config_impl,
    )

    return load_workflow_config_impl(name)


def _default_pipeline_runner_service_factory(
    registry: PipelineRegistry | None,
) -> PipelineRunnerService:
    """Build the pipeline runner service without depending on the facade module."""
    from bioetl.composition.bootstrap.runtime.runner import (
        bootstrap_pipeline_runner_service,
    )

    return bootstrap_pipeline_runner_service(registry=registry)


def get_workflow_runner_service(
    registry: PipelineRegistry | None = None,
    *,
    pipeline_runner_service_factory: Callable[
        [PipelineRegistry | None], PipelineRunnerService
    ]
    | None = None,
) -> WorkflowRunnerService:
    """Build the baseline declarative workflow runner through composition seams."""
    from bioetl.application.services.workflow_runner_service import (
        WorkflowRunnerService,
    )
    from bioetl.application.services.workflow_transform_service import (
        WorkflowTransformService,
    )
    from bioetl.application.workflow.transforms import WorkflowTransformRegistry
    from bioetl.application.workflow.transforms.builtins import (
        register_builtin_workflow_transforms,
    )
    from bioetl.composition.bootstrap.runtime.observability import (
        bootstrap_logger,
    )
    from bioetl.composition.bootstrap.cli.noop import create_noop_logger
    from bioetl.composition.factories.services.port_factories import create_metrics
    from bioetl.infrastructure.storage.silver_writer import SilverWriter
    from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter
    from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
        SilverForeignKeyReconciliationAdapter,
    )

    settings = get_settings()
    metrics = create_metrics(settings)
    transform_storage = SilverWriter(
        base_path=settings.silver_path,
        logger=create_noop_logger(),
        metrics=metrics,
        pipeline_name="workflow_transforms",
    )
    reconciliation_logger = bootstrap_logger("workflow_reconciliation").bind(
        component="workflow_reconciliation",
        adapter="SilverForeignKeyReconciliationAdapter",
    )
    reconciliation_quarantine = UnifiedQuarantineAdapter(
        base_path=str(settings.quarantine_path),
    )
    transform_registry = register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=transform_storage,
            logger=reconciliation_logger,
            metrics=metrics,
            quarantine=reconciliation_quarantine,
            quarantine_pipeline_name="workflow_transforms",
        ),
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
    )


def _get_workflow_memory_lock() -> object:
    global _WORKFLOW_MEMORY_LOCK
    if _WORKFLOW_MEMORY_LOCK is None:
        from bioetl.infrastructure.locking import MemoryLock

        _WORKFLOW_MEMORY_LOCK = MemoryLock()
    return _WORKFLOW_MEMORY_LOCK


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
    from bioetl.composition.factories.services.port_factories import create_metrics
    from bioetl.infrastructure.control_plane import (
        FileWorkflowExecutionStateStore,
        FileWorkflowLedgerStore,
        FileWorkflowManifestStore,
    )
    from bioetl.infrastructure.time import SystemClock

    settings = get_settings()
    metrics = create_metrics(settings)
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
        ),
        workflow_ledger_port=ledger_store,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_store,
        workflow_lock_port=workflow_lock_port
        if workflow_lock_port is not None
        else cast("LockPort", _get_workflow_memory_lock()),
    )


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Get workflow inspection service for operator diagnostics."""
    from bioetl.application.services.control_plane.workflow.inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.composition.factories.services.port_factories import create_metrics
    from bioetl.infrastructure.control_plane import (
        FileWorkflowExecutionStateStore,
        FileWorkflowLedgerStore,
        FileWorkflowManifestStore,
    )

    settings = get_settings()
    metrics = create_metrics(settings)
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
