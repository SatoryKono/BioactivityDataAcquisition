from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.domain.ports import LockPort, MetricsPort
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
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


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        raw_config: dict[str, Any] | None = None,
        **kwargs,  # Accept and ignore extra ports for now
    ) -> PipelineServices:
        """Builds PipelineServices from settings.

        Args:
            settings: Application settings
            logger: Structured logger
            raw_config: Pre-loaded pipeline config dict (avoids duplicate I/O)
            **kwargs: Additional keyword arguments (ignored)

        Returns:
            Configured PipelineServices instance
        """
        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url

        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options if not is_local_run else None
        access_key, secret_key = get_aws_credentials(settings)

        # Use provided config or load from YAML
        raw_config = raw_config or load_pipeline_config("chembl_activity")

        # Convert raw config to typed config for StorageFactory
        pipeline_config = PipelineYamlConfig(
            pipeline_name="chembl_activity",
            provider=raw_config.get("provider", "chembl"),
            entity_type=raw_config.get("entity_type", "activity"),
            primary_keys=raw_config.get("primary_keys", ["activity_id"]),
            silver_table=raw_config.get("silver_table", "chembl.activity"),
            sink=raw_config.get("sink", {}),
        )

        http_client = UnifiedHTTPClient(
            TokenBucket(rate=10.0, capacity=20), CircuitBreaker(provider="chembl")
        )
        data_source = ChemblAdapter(http_client=http_client)

        storage_ctx = StorageFactory.create(settings, pipeline_config, logger)

        lock: LockPort
        if settings.env == "prod":
            logger.info("Using RedisDistributedLock for production environment.")
            redis_client = create_redis_client(settings)
            lock = RedisDistributedLock(redis_client=redis_client)
        else:
            logger.warning(
                "Using MemoryLock. Locking is NOT distributed. Suitable for dev/testing only."
            )
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
        """Creates ChEMBL Activity pipeline with decomposed config.

        Loads config once and passes it through to avoid duplicate I/O.
        """
        # Load config once
        raw_config = load_pipeline_config("chembl_activity")

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=settings, logger=logger, raw_config=raw_config, **kwargs
        )
        # get_pipeline_config uses @lru_cache, so this is cheap
        config = get_pipeline_config("chembl_activity")

        return ChEMBLActivityPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
