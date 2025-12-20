"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use PipelineRunner for execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

# Factories are imported to ensure registration happens
import bioetl.composition.factories.pipeline_factories  # noqa: F401
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.application.orchestration.runner import PipelineRunner
from bioetl.application.registry import PipelineRegistry
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.filter_config import InputFilterConfig
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import get_settings, load_pipeline_config, yaml_config_to_domain
from bioetl.infrastructure.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.infrastructure.factories.storage import StorageAdapter
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
    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
    from bioetl.domain.ports import CheckpointPort, QuarantinePort
    from bioetl.domain.types import RunType
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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
        endpoint_url=settings.aws.endpoint_url
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


def _create_filter_config(
    yaml_config: PipelineYamlConfig,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    logger: structlog.BoundLogger,
) -> InputFilterConfig | None:
    """Create effective filter configuration from CLI args and YAML config."""
    yaml_filter = yaml_config.input_filter
    effective_csv = input_csv or yaml_filter.source_path
    effective_column = filter_column or yaml_filter.column_name
    effective_field = filter_field or yaml_filter.filter_field
    filter_enabled = bool(input_csv) or yaml_filter.enabled

    if filter_enabled and effective_csv:
        logger.info(
            "input_filter_enabled",
            csv_path=effective_csv,
            column=effective_column,
            filter_field=effective_field,
            source="cli" if input_csv else "config",
        )
        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
        )
    return None


def _create_services(
    factory: BasePipelineFactory,
    settings: Settings,
    logger: structlog.BoundLogger,
    yaml_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None,
) -> PipelineServices:
    """Create pipeline services using the factory."""
    return factory.build_services(
        settings=settings,
        logger=logger,
        config=yaml_config,
        filter_config=filter_config,
    )


def _create_pipeline(
    factory: BasePipelineFactory,
    runtime_config: PipelineRuntimeConfig,
    services: PipelineServices,
    yaml_config: PipelineYamlConfig,
) -> BasePipeline:
    """Create the pipeline instance."""
    domain_config = yaml_config_to_domain(yaml_config)
    return factory.pipeline_class.create(
        runtime=runtime_config,
        services=services,
        config=domain_config,
    )


def _create_checkpoint_manager(
    pipeline: BasePipeline,
    run_id: UUID,
    resume: bool,
    logger: structlog.BoundLogger,
) -> CheckpointManager:
    """Create the checkpoint manager."""
    return CheckpointManager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=run_id,
        resume=resume,
        watermark_extractor=lambda record: pipeline.extract_watermark(
            pipeline.context, record
        ),
    )


def _create_executor(
    pipeline: BasePipeline,
    services: PipelineServices,
    checkpoint_manager: CheckpointManager,
    silver_schema: "pa.Schema" | None,
    logger: structlog.BoundLogger,
) -> PipelineExecutor:
    """Create the pipeline executor with record processor."""
    error_classifier = ErrorClassifier()
    dq_config = pipeline.config.dq
    table_config = TableConfig(
        primary_keys=pipeline.config.primary_keys,
        silver_table=pipeline.config.silver_table,
        gold_table=pipeline.config.gold_table,
    )

    record_processor = RecordProcessor(
        services=services,
        error_classifier=error_classifier,
        context=pipeline.context,
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        transform_callback=pipeline.transform_bronze_to_silver,
        gold_filter_callback=pipeline.should_write_gold,
        silver_schema=silver_schema,
        dq_config=dq_config,
        table_config=table_config,
    )

    return PipelineExecutor(
        services=services,
        record_processor=record_processor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        entity_type=pipeline.config.entity_type,
        batch_size=pipeline.config.batch_size,
        checkpoint_interval=pipeline.config.checkpoint_interval,
    )


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
    yaml_config = load_pipeline_config(pipeline_name)

    runtime_config = PipelineRuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        query=query,
    )

    filter_config = _create_filter_config(
        yaml_config, input_csv, filter_column, filter_field, logger
    )

    pipeline_def = PipelineRegistry.get(pipeline_name)
    factory = pipeline_def.factory

    services = _create_services(factory, settings, logger, yaml_config, filter_config)
    pipeline = _create_pipeline(factory, runtime_config, services, yaml_config)

    checkpoint_manager = _create_checkpoint_manager(pipeline, run_id, resume, logger)
    executor = _create_executor(
        pipeline,
        services,
        checkpoint_manager,
        pipeline_def.silver_schema,
        logger,
    )

    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=logger,
        pipeline=pipeline,
        tracer=tracer,
    )
