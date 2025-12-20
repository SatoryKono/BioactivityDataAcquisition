"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use PipelineRunner for execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.application.registry import PipelineRegistry

# Factories are imported to ensure registration happens
from bioetl.composition.factories.chembl_activity import (
    ChEMBLActivityPipelineFactory,
)
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import get_settings, load_pipeline_config
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
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.interfaces.orchestration.runner import PipelineRunner

__all__ = [
    "BronzeWriter",
    "ChEMBLActivityPipelineFactory",
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


def bootstrap_pipeline(
    pipeline_name: str,
    run_id: UUID,
    run_type: RunType,
    resume: bool,
    limit: int | None,
    input_csv: str | None = None,
    filter_column: str | None = None,
    filter_field: str | None = None,
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
    """
    from bioetl.domain.filter_config import InputFilterConfig

    settings = get_settings()
    logger = bootstrap_logger(pipeline=pipeline_name, run_id=run_id)

    # Load validated YAML config
    yaml_config = load_pipeline_config(pipeline_name)

    runtime_config = PipelineRuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
    )

    # Build filter config from YAML defaults, CLI overrides
    filter_config = None
    yaml_filter = yaml_config.input_filter

    # Determine effective values: CLI > YAML config
    effective_csv = input_csv or yaml_filter.source_path
    effective_column = filter_column or yaml_filter.column_name
    effective_field = filter_field or yaml_filter.filter_field

    # Enable filter if: CLI provides --input-csv OR config has enabled=true
    filter_enabled = bool(input_csv) or yaml_filter.enabled

    if filter_enabled and effective_csv:
        filter_config = InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
        )
        logger.info(
            "input_filter_enabled",
            csv_path=effective_csv,
            column=effective_column,
            filter_field=effective_field,
            source="cli" if input_csv else "config",
        )

    # Resolve pipeline factory from registry
    pipeline_def = PipelineRegistry.get(pipeline_name)
    factory = pipeline_def.factory
    silver_schema = pipeline_def.silver_schema

    pipeline = factory.create_with_services(
        runtime=runtime_config,
        settings=settings,
        logger=logger,
        config=yaml_config,
        filter_config=filter_config,
    )

    checkpoint_manager = CheckpointManager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=run_id,
        resume=resume,
        watermark_extractor=lambda record: pipeline.extract_watermark(
            pipeline.context, record
        ),
    )

    error_classifier = ErrorClassifier()

    # 3. Instantiate Executor with typed configs
    dq_config = pipeline.config.dq

    table_config = TableConfig(
        primary_keys=pipeline.config.primary_keys,
        silver_table=pipeline.config.silver_table,
        gold_table=pipeline.config.gold_table,
    )

    record_processor = RecordProcessor(
        services=pipeline.services,
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

    executor = PipelineExecutor(
        services=pipeline.services,
        record_processor=record_processor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        entity_type=pipeline.config.entity_type,
        batch_size=pipeline.config.batch_size,
        checkpoint_interval=pipeline.config.checkpoint_interval,
    )

    runner = PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=logger,
        pipeline=pipeline,  # Explicit dependency injection
    )

    return runner
