# basedpyright residual burn-down (shrink-only product surface).
"""Workflow-specific composition service assembly helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition._workflow_transform_registry import (
    build_workflow_transform_registry,
)
from bioetl.composition.occurrence_identity import (
    create_runtime_occurrence_id,
    create_runtime_occurrence_run_id,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.application.services.workflow.control_plane.execution_service import (
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
    from bioetl.domain.control_plane import WorkflowManifest
    from bioetl.domain.ports import (
        LockPort,
        MetricsPort,
        WorkflowLedgerPort,
    )
    from bioetl.domain.workflow import WorkflowConfig
    from bioetl.infrastructure.config.settings_api import Settings

from bioetl.application.services.control_plane.workflow.ledger_service import (
    WorkflowLedgerService,
)
from bioetl.composition.factories.services.port_factories import (
    WorkflowMetricsFactoryProtocol as _WorkflowMetricsFactory,
)


__all__ = [
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "load_workflow_config",
]
_workflow_memory_lock: LockPort | None = None


def _create_workflow_metrics(settings: Settings) -> MetricsPort:
    """Resolve the patchable metrics factory through a typed lazy boundary."""
    port_factories = import_module(
        "bioetl.composition.factories.services.port_factories"
    )
    candidate: object = port_factories.create_metrics
    if not isinstance(candidate, _WorkflowMetricsFactory):
        raise TypeError("Workflow metrics factory does not satisfy its contract")
    return candidate(settings)


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical composition service seam."""
    workflow_config_api = import_module(
        "bioetl.infrastructure.config.workflow_config_api"
    )

    return workflow_config_api.load_workflow_config(
        name,
        configs_root=resolve_configs_root(),
    )


def _default_pipeline_runner_service_factory(
    registry: PipelineRegistry | None,
) -> PipelineRunnerService:
    """Build the pipeline runner service without depending on the facade module."""
    runner = import_module("bioetl.composition.bootstrap.runtime.runner")

    return runner.bootstrap_pipeline_runner_service(registry=registry)


def get_workflow_runner_service(
    registry: PipelineRegistry | None = None,
    *,
    pipeline_runner_service_factory: Callable[
        [PipelineRegistry | None], PipelineRunnerService
    ]
    | None = None,
) -> WorkflowRunnerService:
    """Build the baseline declarative workflow runner through composition seams."""
    workflow_runner_service = import_module(
        "bioetl.application.services.workflow.workflow_runner_service"
    )
    workflow_transform_service = import_module(
        "bioetl.application.services.workflow.workflow_transform_service"
    )
    control_plane = import_module("bioetl.infrastructure.control_plane")
    infrastructure_time = import_module("bioetl.infrastructure.time")

    settings = get_settings()
    metrics = _create_workflow_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    artifact_sink = control_plane.FileWorkflowTransformArtifactStore(
        base_path=output_root / "workflow_transform_results",
        clock=infrastructure_time.SystemClock(),
    )
    transform_registry = build_workflow_transform_registry(
        settings,
        metrics,
        artifact_sink=artifact_sink,
    )
    pipeline_runner_factory = (
        _default_pipeline_runner_service_factory
        if pipeline_runner_service_factory is None
        else pipeline_runner_service_factory
    )
    return workflow_runner_service.WorkflowRunnerService(
        pipeline_runner=pipeline_runner_factory(registry),
        transform_service=workflow_transform_service.WorkflowTransformService(
            registry=transform_registry,
            metrics=metrics,
        ),
        metrics=metrics,
        workflow_transform_artifact_sink=artifact_sink,
    )


def _get_workflow_memory_lock() -> LockPort:
    global _workflow_memory_lock
    if _workflow_memory_lock is None:
        from bioetl.infrastructure import locking

        _workflow_memory_lock = locking.MemoryLock()
    return _workflow_memory_lock


def _system_clock_now() -> Callable[[], datetime]:
    return import_module("bioetl.infrastructure.time").SystemClock().now


def _create_workflow_ledger_service(
    ledger_port: WorkflowLedgerPort,
    manifest: WorkflowManifest,
) -> WorkflowLedgerService:

    return WorkflowLedgerService(
        ledger_port=ledger_port,
        manifest_id=manifest.manifest_id,
        workflow_run_id=manifest.workflow_run_id,
        workflow_name=manifest.workflow_name,
        _entry_id_factory=lambda: create_runtime_occurrence_id("workflow_ledger_entry"),
        _occurred_at_factory=_system_clock_now(),
    )


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
    workflow_lock_port: LockPort | None = None,
) -> WorkflowExecutionService:
    """Build workflow execution orchestration with durable control-plane seams."""
    execution_service = import_module(
        "bioetl.application.services.workflow.control_plane.execution_service"
    )
    manifest_service_module = import_module(
        "bioetl.application.services.control_plane.workflow.manifest_service"
    )
    control_plane = import_module("bioetl.infrastructure.control_plane")
    infrastructure_time = import_module("bioetl.infrastructure.time")

    settings = get_settings()
    metrics = _create_workflow_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    manifest_store = control_plane.FileWorkflowManifestStore(
        base_path=output_root / "workflow_manifest",
        metrics=metrics,
    )
    ledger_store = control_plane.FileWorkflowLedgerStore(
        base_path=output_root / "workflow_ledger",
        metrics=metrics,
    )
    state_store = control_plane.FileWorkflowExecutionStateStore(
        base_path=output_root / "workflow_state",
        metrics=metrics,
    )
    return execution_service.WorkflowExecutionService(
        workflow_runner=get_workflow_runner_service(registry=registry),
        manifest_service=manifest_service_module.WorkflowManifestService(
            manifest_port=manifest_store,
            clock=infrastructure_time.SystemClock(),
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
        now_factory=infrastructure_time.SystemClock().now,
        run_id_factory=lambda: create_runtime_occurrence_run_id("workflow_execution"),
    )


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Get workflow inspection service for operator diagnostics."""
    inspection_service = import_module(
        "bioetl.application.services.control_plane.workflow.inspection_service"
    )
    control_plane = import_module("bioetl.infrastructure.control_plane")

    settings = get_settings()
    metrics = _create_workflow_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return inspection_service.WorkflowInspectionService(
        manifest_port=control_plane.FileWorkflowManifestStore(
            base_path=output_root / "workflow_manifest",
            metrics=metrics,
        ),
        ledger_port=control_plane.FileWorkflowLedgerStore(
            base_path=output_root / "workflow_ledger",
            metrics=metrics,
        ),
        state_port=control_plane.FileWorkflowExecutionStateStore(
            base_path=output_root / "workflow_state",
            metrics=metrics,
        ),
    )
