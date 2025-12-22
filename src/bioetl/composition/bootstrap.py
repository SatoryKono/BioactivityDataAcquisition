"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use PipelineRunner for execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

# Factories are imported to ensure registration happens
import bioetl.composition.factories.pipeline_factories  # noqa: F401
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.composition.factories.storage_factory import StorageAdapter
from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import get_settings, load_pipeline_config
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.tracing import (
    NoOpTracer,
    OpenTelemetryTracer,
)
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

__all__ = [
    "BronzeWriter",
    "ChemblAdapter",
    "DeltaWriter",
    "GoldWriter",
    "PrometheusMetrics",
    "RedisDistributedLock",
    "S3Checkpoint",
    "StorageAdapter",
    "UnifiedHTTPClient",
    "UnifiedQuarantine",
    "bootstrap_checkpoint",
    "bootstrap_logger",
    "bootstrap_pipeline",
    "bootstrap_quarantine",
    "create_redis_client",
    "get_aws_credentials",
]

if TYPE_CHECKING:
    import structlog

    from bioetl.domain.ports import CheckpointPort, QuarantinePort
    from bioetl.domain.types import RunType
    from bioetl.interfaces.orchestration.runner import PipelineRunner


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine service for CLI inspection."""
    settings = get_settings()
    base_path = f"s3://{settings.s3.bucket_silver}/common/quarantine"
    return UnifiedQuarantine(
        base_path=base_path,
        storage_options=settings.storage_options,
    )


def bootstrap_checkpoint(pipeline_name: str) -> CheckpointPort:
    """Bootstrap the checkpoint service for CLI inspection."""
    settings = get_settings()
    return S3Checkpoint(
        bucket=settings.s3.bucket_checkpoints,
        pipeline_name=pipeline_name,
        endpoint_url=settings.aws.endpoint_url,
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


def bootstrap_pipeline(
    pipeline_name: str,
    run_id: UUID,
    run_type: RunType,
    resume: bool,
    limit: int | None,
    input_csv: str | None = None,
    filter_column: str | None = None,
    filter_field: str | None = None,
    query: str | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    Args:
        pipeline_name: Name of the pipeline to run
        run_id: Unique identifier for this run
        run_type: Type of run (incremental, backfill, rebuild)
        resume: Whether to resume from last checkpoint
        limit: Maximum number of records to process
        input_csv: Optional path to CSV file with filter IDs (overrides config)
        filter_column: Column name in CSV containing filter IDs (overrides config)
        filter_field: API field name to filter by (overrides config)
        query: Optional query string for data sources that support it
    """
    settings = get_settings()
    logger = bootstrap_logger(pipeline=pipeline_name, run_id=run_id)
    tracer = bootstrap_tracer()

    # Load validated YAML config
    yaml_config = load_pipeline_config(pipeline_name)

    runtime_config = RuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        query=query,
    )

    # Build filter config using the dedicated builder
    filter_config = FilterConfigBuilder.build(
        yaml_filter=yaml_config.input_filter,
        cli_csv=input_csv,
        cli_column=filter_column,
        cli_field=filter_field,
    )

    if filter_config:
        logger.info(
            "input_filter_enabled",
            csv_path=filter_config.source_path,
            column=filter_config.column_name,
            filter_field=filter_config.filter_field,
            source="cli" if input_csv else "config",
        )

    # Resolve pipeline factory and delegate runner creation
    pipeline_def = PipelineRegistry.get(pipeline_name)
    factory = pipeline_def.factory

    return factory.create_runner(
        run_id=run_id,
        runtime=runtime_config,
        settings=settings,
        logger=logger,
        tracer=tracer,
        filter_config=filter_config,
        config=yaml_config,
    )
