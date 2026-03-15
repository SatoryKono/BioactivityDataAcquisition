"""Entrypoints for BioETL pipeline operations.

Provides high-level functions for running pipelines and managing resources.
These entrypoints are designed to be used by CLI, REST APIs, or any other
orchestration layer without direct dependency on bootstrap functions.

This module provides the unified pipeline execution interface (REQ-ARCH-041).
Any orchestration layer should use these entrypoints instead of bootstrap.

Split into submodules per audit-package-structure-2026-02-07:
- _pipeline_execution: Core pipeline build/run functions
- _resource_management: Legacy managers, maintenance, inspection
- _services: Application and infrastructure service factories
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

# Re-export canonical DTO classes from application.services (H1 refactoring)
# These are the single source of truth for pipeline execution interfaces.
from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition._pipeline_execution import (
    _require_execution_metrics_runner,
)
from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    build_pipeline_context as _build_pipeline_context,
    create_pipeline_runner as _create_pipeline_runner,
    ensure_metrics_server_started as _ensure_metrics_server_started,
    push_metrics_to_gateway as _push_metrics_to_gateway,
)
from bioetl.composition._resource_management import (
    archive_table,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)
from bioetl.composition._services import (
    cleanup_bronze,
    get_adr_service,
    get_bronze_cleanup_service,
    get_checkpoint_service,
    get_config_service,
    get_export_service,
    get_health_server_dependencies,
    get_health_service,
    get_lock_service,
    get_metrics_service,
    get_pipeline_runner_service,
    get_quarantine_service,
    get_quarantine_store,
    get_vacuum_service,
)
from bioetl.composition.bootstrap import (
    bootstrap_composite_runner,
    load_composite_config,
    load_pipeline_config,
    maybe_start_metrics_server,
)
from bioetl.composition.factories.pipeline.runner import create_metrics_extractor
from bioetl.composition.bootstrap.runtime.observability import start_metrics_server
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "archive_table",
    "bootstrap_composite_runner",
    "build_pipeline_context",
    "cleanup_bronze",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "get_settings",
    "get_adr_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_manager",
    "get_checkpoint_service",
    "get_config_service",
    "get_export_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lifecycle_service",
    "get_lock_service",
    "get_metrics_service",
    "get_pipeline_runner_service",
    "get_quarantine_manager",
    "get_quarantine_service",
    "get_quarantine_store",
    "get_vacuum_service",
    "inspect_quarantine",
    "list_checkpoints",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
    "preview_cleanup",
    "push_metrics_to_gateway",
    "run_pipeline",
    "start_metrics_server",
    "vacuum_table",
]


def build_pipeline_context(name: str, options: RunOptions) -> PipelineRunContext:
    """Compatibility wrapper around the canonical pipeline context builder."""
    return _build_pipeline_context(name, options)


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Compatibility wrapper around the canonical runner factory.

    Kept local so tests can patch ``bioetl.composition.entrypoints.create_pipeline_runner``
    without reaching into the split implementation module.
    """
    return _create_pipeline_runner(name, options)


def ensure_metrics_server_started() -> bool:
    """Compatibility wrapper around the canonical metrics bootstrap helper."""
    return _ensure_metrics_server_started()


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    pipeline_name: str | None = None,
) -> bool:
    """Compatibility wrapper around the canonical metrics push helper."""
    return _push_metrics_to_gateway(run_label=run_label, pipeline_name=pipeline_name)


async def run_pipeline(name: str, options: RunOptions) -> RunResult:
    """Run a pipeline via local wrappers so tests can patch entrypoint symbols."""
    settings = get_settings()
    maybe_start_metrics_server(settings)

    started_at = datetime.now(tz=UTC)
    runner = _require_execution_metrics_runner(create_pipeline_runner(name, options))

    run_id = runner.run_id
    run_type = options.run_type

    status = PipelineRunResult.SUCCESS
    error_message: str | None = None
    error_type: str | None = None

    try:
        await runner.run()
    except PipelineShutdownError:
        status = PipelineRunResult.SHUTDOWN
    except (BioETLError, OSError, RuntimeError, ValueError, TypeError) as exc:
        status = PipelineRunResult.FAILED
        error_message = str(exc)
        error_type = type(exc).__name__

    completed_at = datetime.now(tz=UTC)
    metrics = create_metrics_extractor().extract_metrics(runner)
    return RunResult(
        status=status,
        pipeline_name=name,
        run_id=run_id,
        run_type=run_type,
        records_fetched=int(metrics.get("records_fetched", 0)),
        records_bronze=int(metrics.get("records_bronze", 0)),
        records_silver=int(metrics.get("records_silver", 0)),
        records_gold=int(metrics.get("records_gold", 0)),
        records_quarantined=int(metrics.get("records_quarantined", 0)),
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
        error_type=error_type,
    )
