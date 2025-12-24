"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use PipelineRunner for execution.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.factories.storage_factory import StorageAdapter
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.registry import PipelineRegistry
from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings, load_pipeline_config
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.server import start_metrics_server
from bioetl.infrastructure.observability.tracing import NoOpTracer, OpenTelemetryTracer
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

__all__ = [
    "BronzeWriter",
    "ChemblAdapter",
    "DeltaWriter",
    "GoldWriter",
    "LocalCheckpoint",
    "MemoryLock",
    "ObservabilityBundle",
    "PrometheusMetrics",
    "StorageAdapter",
    "UnifiedHTTPClient",
    "UnifiedQuarantine",
    "bootstrap_checkpoint",
    "bootstrap_cleanup",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    "bootstrap_pipeline",
    "bootstrap_quarantine",
    "bootstrap_storage",
]

if TYPE_CHECKING:
    from uuid import UUID

    import structlog

    from bioetl.application.core.cleanup_service import CleanupService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        CheckpointPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings


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


def bootstrap_storage() -> StorageAdapter:
    """Bootstrap a read-only storage adapter for CLI operations.

    Creates a minimal StorageAdapter suitable for preview operations.
    No CSV export is configured since this is for read-only inspection.
    Uses NoOpLogger since this is for CLI preview operations without observability.

    Returns:
        StorageAdapter configured for the current environment.
    """
    settings = get_settings()
    noop_logger = NoOpLogger()

    return StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=settings.bronze_path,
            logger=noop_logger,
            save_json=False,
            json_path=None,
        ),
        silver_writer=DeltaWriter(
            base_path=settings.silver_path,
            csv_exporter=None,
            logger=noop_logger,
        ),
        gold_writer=GoldWriter(
            base_path=settings.gold_path,
            csv_exporter=None,
        ),
    )


def bootstrap_cleanup() -> CleanupService:
    """Bootstrap the cleanup service for CLI operations.

    Creates a CleanupService with storage and logger for cleanup operations.
    Used by CLI for --dry-run preview and actual cleanup.

    Returns:
        CleanupService configured for the current environment.
    """
    from bioetl.application.core.cleanup_service import CleanupService

    storage = bootstrap_storage()
    noop_logger = NoOpLogger()

    return CleanupService(storage=storage, logger=noop_logger)


def bootstrap_logger(
    pipeline: str, run_id: UUID, log_level: str = "INFO"
) -> structlog.BoundLogger:
    """Create a logger for the application layer (e.g., CLI)."""
    return create_infra_logger(
        pipeline=pipeline, run_id=run_id, log_level=log_level, json_format=True
    )


def bootstrap_tracer(service_name: str = "bioetl") -> TracingPort:
    """Bootstrap distributed tracing."""
    settings = get_settings()
    if settings.observability.tracing_enabled:
        try:
            return OpenTelemetryTracer(service_name=service_name)
        except ImportError:
            # OpenTelemetry not installed, fall back to no-op
            pass
    return NoOpTracer()


def bootstrap_metrics(settings: Settings) -> MetricsPort | None:
    """Bootstrap metrics with optional server start.

    Server is started only if explicitly enabled in settings.

    Args:
        settings: Application settings.

    Returns:
        MetricsPort instance or None if metrics are disabled.
    """
    if not settings.observability.metrics_enabled:
        return None

    metrics = PrometheusMetrics()

    if settings.observability.metrics_server_enabled:
        # Log but don't fail - metrics collection still works
        with contextlib.suppress(Exception):
            start_metrics_server(settings.metrics_port)

    return metrics


def bootstrap_observability(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
) -> ObservabilityBundle:
    """Bootstrap all observability components.

    Creates a unified observability bundle containing logger, tracer, and metrics.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier.
        settings: Application settings.

    Returns:
        Configured ObservabilityBundle instance.
    """
    logger = bootstrap_logger(pipeline=pipeline, run_id=run_id)
    tracer = bootstrap_tracer()
    metrics = bootstrap_metrics(settings)

    return ObservabilityBundle(logger=logger, tracer=tracer, metrics=metrics)


def bootstrap_pipeline(ctx: PipelineRunContext) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    Args:
        ctx: Pipeline run context containing launch parameters
    """
    # Explicit registration (idempotent)
    register_all_pipelines()

    settings = get_settings()

    # Bootstrap unified observability (includes metrics server start if enabled)
    observability = bootstrap_observability(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
    )

    # Load validated YAML config
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    runtime_config = RuntimeConfig(
        run_type=ctx.run_type,
        resume=ctx.resume,
        limit=ctx.limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        query=ctx.query,
        dry_run=ctx.dry_run,
    )

    # Build filter config using the dedicated builder
    filter_config = FilterConfigBuilder.build(
        yaml_filter=yaml_config.input_filter,
        cli_csv=ctx.input_csv,
        cli_column=ctx.filter_column,
        cli_field=ctx.filter_field,
    )

    if filter_config:
        observability.logger.info(
            "input_filter_enabled",
            csv_path=filter_config.source_path,
            column=filter_config.column_name,
            filter_field=filter_config.filter_field,
            source="cli" if ctx.input_csv else "config",
        )

    # Resolve pipeline factory and delegate runner creation
    pipeline_def = PipelineRegistry.get(ctx.pipeline_name)
    factory = pipeline_def.factory

    return factory.create_runner(
        run_id=ctx.run_id,
        runtime=runtime_config,
        settings=settings,
        observability=observability,
        filter_config=filter_config,
        config=yaml_config,
    )
