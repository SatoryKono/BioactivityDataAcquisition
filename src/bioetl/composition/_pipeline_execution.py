"""Pipeline execution entrypoints for building, configuring, and running ETL."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.composition.registry_api import PipelineRegistry

from bioetl.composition._registration import ensure_runtime_registrations
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    build_pipeline_context as build_pipeline_context_impl,
)
from bioetl.composition.factories.pipeline.runner import create_metrics_extractor
from bioetl.composition.observability_runtime import (
    push_metrics_to_gateway as push_metrics_to_gateway_impl,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.ports import ExecutionMetricsRunnerPort
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import ClockPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config.settings_api import Settings


__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "push_metrics_to_gateway",
    "run_pipeline",
]


def get_settings() -> Settings:
    """Resolve runtime settings lazily while keeping a patchable module seam."""
    from bioetl.composition.runtime_builders.config_access import get_settings as impl

    return impl()


def maybe_start_metrics_server(settings: Settings) -> bool:
    """Resolve metrics-server startup lazily while keeping a patchable seam."""
    from bioetl.composition.bootstrap.runtime.observability import (
        maybe_start_metrics_server as impl,
    )

    return impl(settings)


def build_pipeline_context(
    name: str,
    options: RunOptions,
    *,
    run_id: RunID | UUID | str | None = None,
    run_id_factory: Callable[[], RunID | UUID | str] | None = None,
    clock: ClockPort | None = None,
    started_at: datetime | None = None,
) -> PipelineRunContext:
    """Forward to the canonical runtime context builder lazily."""

    return build_pipeline_context_impl(
        name,
        options,
        run_id=run_id,
        run_id_factory=run_id_factory,
        clock=clock,
        started_at=started_at,
    )


def _ensure_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered for shared entrypoints."""

    ensure_runtime_registrations(registry=registry)


def _require_execution_metrics_runner(
    runner: object,
) -> ExecutionMetricsRunnerPort:
    """Validate that the created runner is runnable and metrics-readable."""

    if not isinstance(runner, ExecutionMetricsRunnerPort):
        raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
    return runner


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    pipeline_name: str | None = None,
    run_type: str | None = None,
    grouping_key_extra: dict[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
) -> bool:
    """Push current metrics to Prometheus Pushgateway via composition.

    Args:
        run_label: Run label for pushed metrics.
        pipeline_name: Pipeline name for grouping (e.g. "chembl_molecule").
        run_type: Optional run type for grouping (e.g. "incremental").

    Returns:
        True if push succeeded, False otherwise.
    """

    return push_metrics_to_gateway_impl(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
        grouping_key_extra=grouping_key_extra,
        metric_names=metric_names,
    )


def ensure_metrics_server_started() -> bool:
    """Ensure metrics server is started if enabled in settings.

    Returns:
        True if server was started or already running, False if disabled.
    """
    settings = get_settings()
    return bool(maybe_start_metrics_server(settings))


@dataclass(frozen=True)
class VacuumOptions:
    """Options for vacuum operation."""

    retention_days: int = 7
    dry_run: bool = False


@dataclass(frozen=True)
class ArchiveOptions:
    """Options for archive operation."""

    target_path: str
    remove_source: bool = False


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Create a pipeline runner for the given pipeline and options.

    This is the main entrypoint for pipeline execution. It handles:
    - Registration of providers and pipelines
    - Building the pipeline context
    - Bootstrapping the runner with all dependencies

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        ExecutionMetricsRunnerPort ready for execution via runner.run().

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> runner = create_pipeline_runner("chembl_activity", options)
        >>> await runner.run()
    """

    run_context = build_pipeline_context(
        name,
        options,
        clock=SystemClock(),
    )
    return _create_pipeline_runner_from_context(run_context)


def _create_pipeline_runner_from_context(
    run_context: PipelineRunContext,
) -> ExecutionMetricsRunnerPort:
    """Build a runnable pipeline runner from a prepared execution context."""

    return _require_execution_metrics_runner(bootstrap_pipeline_runner(run_context))


async def run_pipeline(name: str, options: RunOptions) -> RunResult:
    """Run pipeline end-to-end and return structured execution result.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options controlling execution behaviour.

    Returns:
        RunResult with execution status, record counts, and timing information.
    """

    run_context = build_pipeline_context(
        name,
        options,
        clock=SystemClock(),
    )
    started_at, started_monotonic = capture_runtime_timing_anchor(
        started_at=run_context.started_at,
        clock=SystemClock(),
    )

    # Extract run context for result
    run_type = options.run_type
    run_id = str(run_context.run_id)

    status = PipelineRunResult.SUCCESS
    error_message: str | None = None
    error_type: str | None = None
    runner: ExecutionMetricsRunnerPort | None = None

    try:
        runner = _require_execution_metrics_runner(
            _create_pipeline_runner_from_context(run_context)
        )
    except (
        BioETLError,
        ImportError,
        LookupError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as e:
        status = PipelineRunResult.FAILED
        error_message = str(e)
        error_type = type(e).__name__
    else:
        try:
            await runner.run()
        except PipelineShutdownError:
            status = PipelineRunResult.SHUTDOWN
        except (BioETLError, OSError, RuntimeError, ValueError, TypeError) as e:
            status = PipelineRunResult.FAILED
            error_message = str(e)
            error_type = type(e).__name__

    completed_at, _ = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )

    metrics = (
        create_metrics_extractor().extract_metrics(runner) if runner is not None else {}
    )
    result = RunResult(
        status=status,
        pipeline_name=name,
        run_id=run_id,
        run_type=run_type,
        records_fetched=int(metrics.get("records_fetched", 0)),
        records_bronze=int(metrics.get("records_bronze", 0)),
        records_silver=int(metrics.get("records_silver", 0)),
        records_gold=int(metrics.get("records_gold", 0)),
        records_gold_excluded_by_contract=int(
            metrics.get("records_gold_excluded_by_contract", 0)
        ),
        records_quarantined=int(metrics.get("records_quarantined", 0)),
        records_filtered_out=int(metrics.get("records_filtered_out", 0)),
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
        error_type=error_type,
    )
    settings = get_settings()
    if settings.observability.metrics_enabled:
        push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name=name,
            run_type=run_type,
        )
    return result
