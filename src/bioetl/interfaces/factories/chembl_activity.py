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


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        config: PipelineYamlConfig | None = None,
        **kwargs,  # Accept and ignore extra ports for now
    ) -> PipelineServices:
        """Builds PipelineServices from settings.

        Args:
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
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
        pipeline_config = config or load_pipeline_config("chembl_activity")
        sink_config = pipeline_config.sink
        bronze_config = sink_config.get("bronze")
        silver_config = sink_config.get("silver")
        gold_config = sink_config.get("gold")

        http_client = UnifiedHTTPClient(
            TokenBucket(rate=10.0, capacity=20), CircuitBreaker(provider="chembl")
        )
        data_source = ChemblAdapter(http_client=http_client)

        if is_local_run:
            logger.info(
                "Local run detected. Overriding storage paths to 'data/output'."
            )
            base_output_path = "data/output"
            bronze_path = f"{base_output_path}/bronze"
            silver_base_path = f"{base_output_path}/silver"
            gold_base_path = f"{base_output_path}/gold"
            checkpoints_path = f"{base_output_path}/checkpoints"

            save_json = bronze_config.save_json if bronze_config else False
            json_path = (
                f"{base_output_path}/json" if save_json else None
            )

            # Get CSV export config for each layer
            silver_csv_config = silver_config.csv_export if silver_config else None
            silver_csv_path = (
                silver_csv_config.path
                if silver_csv_config and silver_csv_config.enabled
                else None
            )
            silver_csv_options = (
                {
                    "delimiter": silver_csv_config.delimiter,
                    "header": silver_csv_config.header,
                    "encoding": silver_csv_config.encoding,
                }
                if silver_csv_path and silver_csv_config
                else None
            )

            gold_csv_config = gold_config.csv_export if gold_config else None
            gold_csv_path = (
                gold_csv_config.path if gold_csv_config and gold_csv_config.enabled else None
            )
            gold_csv_options = (
                {
                    "delimiter": gold_csv_config.delimiter,
                    "header": gold_csv_config.header,
                    "encoding": gold_csv_config.encoding,
                }
                if gold_csv_path and gold_csv_config
                else None
            )
        else:
            # For cloud runs, use S3 paths from config
            bronze_path = s3_config.bucket_bronze
            silver_base_path = f"s3://{s3_config.bucket_silver}"
            gold_base_path = f"s3://{s3_config.bucket_gold}"
            checkpoints_path = s3_config.bucket_checkpoints
            json_path = None  # JSON path is handled differently for S3
            silver_csv_path = None  # No CSV export for cloud runs by default
            silver_csv_options = None
            gold_csv_path = None
            gold_csv_options = None

        # Get save_json flag from bronze config
        save_json = bronze_config.save_json if bronze_config else False
        if save_json:
            logger.info("JSON export enabled for Bronze layer")

        if silver_csv_path:
            logger.info(f"CSV export enabled for Silver layer: {silver_csv_path}")

        if gold_csv_path:
            logger.info(f"CSV export enabled for Gold layer: {gold_csv_path}")

        storage = StorageAdapter(
            BronzeWriter(
                bucket=bronze_path,
                endpoint_url=aws_config.endpoint_url if not is_local_run else None,
                access_key=access_key,
                secret_key=secret_key,
                save_json=save_json,
                json_path=json_path,
                logger=logger,
            ),
            DeltaWriter(
                base_path=silver_base_path,
                storage_options=storage_options,
                csv_path=silver_csv_path,
                csv_options=silver_csv_options,
            ),
            GoldWriter(
                base_path=gold_base_path,
                storage_options=storage_options,
                csv_path=gold_csv_path,
                csv_options=gold_csv_options,
            ),
        )

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
        """Creates ChEMBL Activity pipeline with decomposed config.

        Loads config once and passes it through to avoid duplicate I/O.
        """
        # Load config once
        config_model = load_pipeline_config("chembl_activity")

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=settings, logger=logger, config=config_model, **kwargs
        )
        # get_pipeline_config uses @lru_cache, so this is cheap
        config = get_pipeline_config("chembl_activity")

        return ChEMBLActivityPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
