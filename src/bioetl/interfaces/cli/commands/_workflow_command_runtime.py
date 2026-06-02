"""Runtime helpers for workflow CLI command execution."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from bioetl.interfaces.cli.commands._workflow_run_support import (
    _execute_workflow_and_publish_metrics,
    _handle_workflow_result,
)
from bioetl.interfaces.cli.commands._workflow_support import render_run_result
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    build_observability_backend_required_probe_paths,
    ensure_observability_backend_started,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.control_plane.workflow.execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.composition.registry_api import PipelineRegistry


def workflow_pipeline_probe_paths(config: WorkflowConfig) -> tuple[str, ...]:
    """Return required observability probe paths for pipeline steps in one workflow."""
    pipelines = tuple(
        step.pipeline_name
        for step in config.steps
        if isinstance(step, WorkflowStepConfig)
    )
    return build_observability_backend_required_probe_paths(pipelines=pipelines)


def execute_workflow_with_backend(
    *,
    config: WorkflowConfig,
    registry: PipelineRegistry | None,
    dry_run: bool,
    only_steps: str | None,
    resume_last: bool,
    resume_manifest_id: str | None,
    resume_run_id: UUID | None,
    force_steps: str | None,
    repair_steps: str | None,
    incremental: bool,
    ensure_observability_backend: bool,
    observability_backend_port: int,
    get_workflow_execution_service_fn: Callable[..., WorkflowExecutionService],
    ensure_metrics_server_started_fn: Callable[[], object],
    publish_metrics_safely_fn: Callable[..., object],
) -> None:
    """Run one workflow after optional observability-backend bootstrap."""
    ensure_observability_backend_started(
        enabled=ensure_observability_backend,
        port=observability_backend_port,
        required_probe_paths=workflow_pipeline_probe_paths(config),
    )
    result = _execute_workflow_and_publish_metrics(
        get_workflow_execution_service_fn=get_workflow_execution_service_fn,
        ensure_metrics_server_started_fn=ensure_metrics_server_started_fn,
        publish_metrics_safely_fn=publish_metrics_safely_fn,
        config=config,
        registry=registry,
        dry_run=dry_run,
        only_steps=only_steps,
        resume_last=resume_last,
        resume_manifest_id=resume_manifest_id,
        resume_run_id=resume_run_id,
        force_steps=force_steps,
        repair_steps=repair_steps,
        incremental=incremental,
    )
    render_run_result(
        config,
        result,
        dry_run=dry_run,
        only_steps=only_steps,
        resume_last=resume_last,
    )
    _handle_workflow_result(result)


__all__ = ["execute_workflow_with_backend", "workflow_pipeline_probe_paths"]
