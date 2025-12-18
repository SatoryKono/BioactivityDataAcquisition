from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.pubchem_compound import PubChemCompoundPipeline
from bioetl.domain.ports import LockPort, MetricsPort
from bioetl.infrastructure.adapters.pubchem.client import PubChemClient
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
from bioetl.infrastructure.factories.storage_factory import StorageFactory
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    import structlog


class PubChemCompoundPipelineFactory:
    """Factory for creating PubChem Compound pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        raw_config: dict[str, Any] | None = None,
        **kwargs,
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""
        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url
        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options if not is_local_run else None
        access_key, secret_key = get_aws_credentials(settings)

        # Use provided config or load from YAML
        raw_config = raw_config or load_pipeline_config("pubchem_compound")

        # Convert raw config to typed config for StorageFactory
        pipeline_config = PipelineYamlConfig(
            pipeline_name="pubchem_compound",
            provider=raw_config.get("provider", "pubchem"),
            entity_type=raw_config.get("entity_type", "compound"),
            primary_keys=raw_config.get("primary_keys", ["cid"]),
            silver_table=raw_config.get("silver_table", "pubchem.compound"),
            sink=raw_config.get("sink", {}),
        )

        # Configure data source
        data_source = PubChemClient(
            rate=raw_config.get("source", {}).get("api", {}).get("rate_limit", 5.0)
        )

        storage_ctx = StorageFactory.create(settings, pipeline_config, logger)

        lock: LockPort
        if settings.env == "prod":
            redis_client = create_redis_client(settings)
            lock = RedisDistributedLock(redis_client=redis_client)
        else:
            lock = MemoryLock()

        checkpoint = S3Checkpoint(
            bucket=storage_ctx.checkpoints_path,
            endpoint_url=aws_config.endpoint_url if not is_local_run else None,
            access_key=access_key,
            secret_key=secret_key,
        )
        quarantine = UnifiedQuarantine(
            base_path=f"{storage_ctx.silver_path}/common/quarantine",
            storage_options=storage_options,
        )
        metrics: MetricsPort = (
            PrometheusMetrics()
            if getattr(settings, "metrics", None) and settings.metrics.enabled
            else NoOpMetrics()
        )

        return PipelineServices(
            data_source=data_source,
            storage=storage_ctx.adapter,
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
        """Creates PubChem Compound pipeline."""
        raw_config = load_pipeline_config("pubchem_compound")
        services = PubChemCompoundPipelineFactory.build_services(
            settings=settings, logger=logger, raw_config=raw_config, **kwargs
        )
        config = get_pipeline_config("pubchem_compound")

        return PubChemCompoundPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
