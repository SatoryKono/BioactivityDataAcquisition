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
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.interfaces.factories.chembl_activity import (
    ChEMBLActivityPipelineFactory,
)
from bioetl.interfaces.factories.pubchem_compound import (
    PubChemCompoundPipelineFactory,
)
from bioetl.interfaces.factories.uniprot_protein import (
    UniProtProteinPipelineFactory,
)
from bioetl.interfaces.orchestration.runner import PipelineRunner
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import get_settings
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
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

# Explicit exports for test mocking
__all__ = [
    "bootstrap_logger",
    "bootstrap_pipeline",
    "ChemblAdapter",
    "UnifiedHTTPClient",
    "S3Checkpoint",
    "ChEMBLActivityPipelineFactory",
    "create_redis_client",
    "get_aws_credentials",
    "StorageAdapter",
    "RedisDistributedLock",
    "PrometheusMetrics",
    "UnifiedQuarantine",
    "BronzeWriter",
    "DeltaWriter",
    "GoldWriter",
    "bootstrap_quarantine",
    "bootstrap_checkpoint",
]

if TYPE_CHECKING:
    import structlog
    from bioetl.domain.types import RunType
    from bioetl.domain.ports import QuarantinePort, CheckpointPort


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine service for CLI inspection."""
    settings = get_settings()
    # Using silver bucket/common/quarantine as per design
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
) -> PipelineRunner:
    """
    Composition Root: Assembles and returns a fully configured PipelineRunner.

    This function wires together:
    1. Infrastructure Adapters (via PipelineServices)
    2. Domain Logic (via BasePipeline subclass)
    3. Application Managers (Checkpoint, Quarantine, ErrorClassifier)
    4. Execution Engine (PipelineExecutor)
    5. Orchestration (PipelineRunner)
    """
    settings = get_settings()
    logger = bootstrap_logger(pipeline=pipeline_name, run_id=run_id)

    runtime_config = PipelineRuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
    )

    # 1. Create the pipeline definition (Logic + Config + Services)
    silver_schema = None
    if pipeline_name == "chembl_activity":
        pipeline = ChEMBLActivityPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
        silver_schema = CHEMBL_ACTIVITY_SCHEMA
    elif pipeline_name == "pubchem_compound":
        pipeline = PubChemCompoundPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
        silver_schema = PUBCHEM_COMPOUND_SCHEMA
    elif pipeline_name == "uniprot_protein":
        pipeline = UniProtProteinPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
        silver_schema = UNIPROT_PROTEIN_SCHEMA
    else:
        raise ValueError(f"Unknown pipeline name: {pipeline_name}")

    # 2. Instantiate Application Managers
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

    quarantine_manager = QuarantineManager(
        quarantine_port=pipeline.services.quarantine,
        pipeline_name=pipeline.config.pipeline_name,
    )

    error_classifier = ErrorClassifier()

    # 3. Instantiate Executor
    dq_config = {
        "silver_table": pipeline.config.silver_table,
        "gold_table": pipeline.config.gold_table,
        # Default thresholds; could be exposed in config later
        "soft_fail_threshold": 0.05,
        "hard_fail_threshold": 0.20,
    }

    executor = PipelineExecutor(
        data_source=pipeline.services.data_source,
        storage=pipeline.services.storage,
        checkpoint_manager=checkpoint_manager,
        quarantine_manager=quarantine_manager,
        error_classifier=error_classifier,
        context=pipeline.context,
        shutdown_signal=pipeline.shutdown_signal,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        transform_callback=pipeline.transform_bronze_to_silver,
        gold_filter_callback=pipeline.should_write_gold,
        silver_schema=silver_schema,
        batch_size=pipeline.config.batch_size,
        checkpoint_interval=pipeline.config.checkpoint_interval,
        metrics=pipeline.services.metrics,
        dq_config=dq_config,
    )

    # 4. Instantiate Runner
    runner = PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=logger,
    )
    # Expose original pipeline for tests/introspection
    setattr(runner, "pipeline", pipeline)

    return runner
