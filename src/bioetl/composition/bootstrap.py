"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use PipelineRunner for execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Factories are imported to ensure registration happens
import bioetl.composition.factories.pipeline_factories  # noqa: F401
from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.storage_factory import StorageAdapter
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
    "PrometheusMetrics",
    "StorageAdapter",
    "UnifiedHTTPClient",
    "UnifiedQuarantine",
    "bootstrap_checkpoint",
    "bootstrap_logger",
    "bootstrap_pipeline",
    "bootstrap_quarantine",
]

if TYPE_CHECKING:
    from uuid import UUID

    import structlog

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import CheckpointPort, QuarantinePort


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


def bootstrap_logger(
    pipeline: str, run_id: UUID, log_level: str = "INFO"
) -> structlog.BoundLogger:
    """Create a logger for the application layer (e.g., CLI)."""
    return create_infra_logger(
        pipeline=pipeline, run_id=run_id, log_level=log_level, json_format=True
    )


def bootstrap_tracer(service_name: str = "bioetl"):
    """Bootstrap distributed tracing."""
    settings = get_settings()
    if settings.observability.tracing_enabled:
        return OpenTelemetryTracer(service_name=service_name)
    return NoOpTracer()


def bootstrap_pipeline(ctx: PipelineRunContext) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    Args:
        ctx: Pipeline run context containing launch parameters
    """
    settings = get_settings()
    logger = bootstrap_logger(pipeline=ctx.pipeline_name, run_id=ctx.run_id)
    tracer = bootstrap_tracer()

    # Load validated YAML config
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    runtime_config = RuntimeConfig(
        run_type=ctx.run_type,
        resume=ctx.resume,
        limit=ctx.limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        query=ctx.query,
    )

    # Ensure metrics server is running (idempotent call)
    # This guarantees observability even if pipeline is run programmatically (outside CLI)
    try:
        start_metrics_server(settings.metrics_port)
    except Exception as e:
        # Don't block pipeline startup if metrics fail, but log it
        logger.warning("failed_to_start_metrics_server", error=str(e))

    # Build filter config using the dedicated builder
    filter_config = FilterConfigBuilder.build(
        yaml_filter=yaml_config.input_filter,
        cli_csv=ctx.input_csv,
        cli_column=ctx.filter_column,
        cli_field=ctx.filter_field,
    )

    if filter_config:
        logger.info(
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
        logger=logger,
        tracer=tracer,
        filter_config=filter_config,
        config=yaml_config,
    )
