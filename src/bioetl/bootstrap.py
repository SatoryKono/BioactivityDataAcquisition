"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl_activity import CHEMBL_ACTIVITY_CONFIG
from bioetl.infrastructure.config import Settings, get_settings
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

if TYPE_CHECKING:
    from uuid import UUID

    import structlog

    from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
    from bioetl.domain.types import RunType


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
) -> BasePipeline:
    """
    Composition Root: Assembles and returns a fully configured pipeline instance.
    """
    settings = get_settings()
    logger = bootstrap_logger(pipeline=pipeline_name, run_id=run_id)

    runtime_config = PipelineRuntimeConfig(
        run_type=run_type, resume=resume, limit=limit
    )

    if pipeline_name == "chembl_activity":
        pipeline = ChEMBLActivityPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
    else:
        raise ValueError(f"Unknown pipeline name: {pipeline_name}")

    return pipeline


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        **kwargs,  # Accept and ignore extra ports for now
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""
        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options
        access_key, secret_key = get_aws_credentials(settings)

        http_client = UnifiedHTTPClient(
            TokenBucket(rate=10.0, capacity=20), CircuitBreaker(provider="chembl")
        )
        data_source = ChemblAdapter(http_client=http_client)

        storage = StorageAdapter(
            BronzeWriter(
                bucket=s3_config.bucket_bronze,
                endpoint_url=aws_config.endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
            ),
            DeltaWriter(
                base_path=f"s3://{s3_config.bucket_silver}",
                storage_options=storage_options,
            ),
            GoldWriter(
                base_path=f"s3://{s3_config.bucket_gold}",
                storage_options=storage_options,
            ),
        )

        redis_client = create_redis_client(settings)
        lock = RedisDistributedLock(redis_client=redis_client)
        checkpoint = S3Checkpoint(
            bucket=s3_config.bucket_checkpoints,
            endpoint_url=aws_config.endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
        )
        quarantine = UnifiedQuarantine(
            base_path=f"s3://{s3_config.bucket_silver}/common/quarantine",
            storage_options=storage_options,
        )
        metrics: MetricsPort = (
            PrometheusMetrics(port=settings.metrics.port)
            if settings.metrics.enabled
            else NoOpMetrics()
        )

        return PipelineServices(
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics,
            logger=logger,
        )

    @staticmethod
    def create_with_services(
        runtime: PipelineRuntimeConfig,
        settings: Settings,
        logger: "structlog.BoundLogger",
        **kwargs,
    ) -> "ChEMBLActivityPipeline":
        """Creates ChEMBL Activity pipeline with decomposed config."""
        from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=settings, logger=logger, **kwargs
        )

        # Inject infrastructure settings into pipeline config
        config = replace(
            CHEMBL_ACTIVITY_CONFIG,
            heartbeat_interval=settings.pipeline.heartbeat_interval,
        )

        return ChEMBLActivityPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
