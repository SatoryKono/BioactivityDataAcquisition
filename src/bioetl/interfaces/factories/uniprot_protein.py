from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.uniprot_protein import UniProtProteinPipeline
from bioetl.domain.ports import LockPort, MetricsPort
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import (
    Settings,
    get_pipeline_config,
    load_pipeline_config,
)
from bioetl.infrastructure.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    import structlog


class UniProtProteinPipelineFactory:
    """Factory for creating UniProt Protein pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        config: PipelineYamlConfig | None = None,
        **kwargs,
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""
        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url
        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options if not is_local_run else None
        access_key, secret_key = get_aws_credentials(settings)

        pipeline_config = config or load_pipeline_config("uniprot_protein")

        # Configure data source
        source_config = pipeline_config.source.get("api", {})
        data_source = UniProtClient(
            rate=source_config.get("rate_limit", 10.0),
            base_url=source_config.get("base_url", "https://rest.uniprot.org")
        )

        if is_local_run:
            base_output_path = "data/output"
            bronze_path = f"{base_output_path}/bronze"
            silver_base_path = f"{base_output_path}/silver"
            gold_base_path = f"{base_output_path}/gold"
            checkpoints_path = f"{base_output_path}/checkpoints"
        else:
            bronze_path = s3_config.bucket_bronze
            silver_base_path = f"s3://{s3_config.bucket_silver}"
            gold_base_path = f"s3://{s3_config.bucket_gold}"
            checkpoints_path = s3_config.bucket_checkpoints

        storage = StorageAdapter(
            BronzeWriter(
                bucket=bronze_path,
                endpoint_url=aws_config.endpoint_url if not is_local_run else None,
                access_key=access_key,
                secret_key=secret_key,
                logger=logger,
            ),
            DeltaWriter(base_path=silver_base_path, storage_options=storage_options),
            GoldWriter(base_path=gold_base_path, storage_options=storage_options),
        )

        lock: LockPort
        if settings.env == "prod":
            redis_client = create_redis_client(settings)
            lock = RedisDistributedLock(redis_client=redis_client)
        else:
            lock = MemoryLock()

        checkpoint = S3Checkpoint(
            bucket=checkpoints_path,
            endpoint_url=aws_config.endpoint_url if not is_local_run else None,
            access_key=access_key,
            secret_key=secret_key,
        )
        quarantine = UnifiedQuarantine(
            base_path=f"{silver_base_path}/common/quarantine",
            storage_options=storage_options,
        )
        metrics: MetricsPort = (
            PrometheusMetrics()
            if getattr(settings, "metrics", None) and settings.metrics.enabled
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
    ) -> BasePipeline:
        """Creates UniProt Protein pipeline."""
        config_model = load_pipeline_config("uniprot_protein")
        services = UniProtProteinPipelineFactory.build_services(
            settings=settings, logger=logger, config=config_model, **kwargs
        )
        config = get_pipeline_config("uniprot_protein")

        return UniProtProteinPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
