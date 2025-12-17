"""Factory for creating ChEMBL Activity pipelines."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path
import yaml

from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl_activity import CHEMBL_ACTIVITY_CONFIG
from bioetl.domain.ports import LockPort, MetricsPort
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import Settings
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

if TYPE_CHECKING:
    import structlog
    from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline


def load_pipeline_config(pipeline_name: str) -> dict[str, Any]:
    """Load pipeline configuration from YAML file.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')

    Returns:
        Dictionary with pipeline configuration
    """
    # Map pipeline name to config path
    config_paths = {
        "chembl_activity": Path("configs/pipelines/chembl/activity.yaml"),
    }

    config_path = config_paths.get(pipeline_name)
    if not config_path or not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        **kwargs,  # Accept and ignore extra ports for now
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""
        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url

        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options if not is_local_run else None
        access_key, secret_key = get_aws_credentials(settings)

        # Load pipeline config from YAML
        pipeline_config = load_pipeline_config("chembl_activity")
        sink_config = pipeline_config.get("sink", {})
        bronze_config = sink_config.get("bronze", {})

        http_client = UnifiedHTTPClient(
            TokenBucket(rate=10.0, capacity=20), CircuitBreaker(provider="chembl")
        )
        data_source = ChemblAdapter(http_client=http_client)

        if is_local_run:
            logger.info("Local run detected. Overriding storage paths to 'data/output'.")
            base_output_path = "data/output"
            bronze_path = f"{base_output_path}/bronze"
            silver_base_path = f"{base_output_path}/silver"
            gold_base_path = f"{base_output_path}/gold"
            checkpoints_path = f"{base_output_path}/checkpoints"
            csv_path = f"{base_output_path}/csv"
            json_path = f"{base_output_path}/json" if bronze_config.get("save_json") else None
        else:
            # For cloud runs, use S3 paths from config
            bronze_path = s3_config.bucket_bronze
            silver_base_path = f"s3://{s3_config.bucket_silver}"
            gold_base_path = f"s3://{s3_config.bucket_gold}"
            checkpoints_path = s3_config.bucket_checkpoints
            csv_path = None  # No CSV export for cloud runs by default
            json_path = None  # JSON path is handled differently for S3

        # Get save_json flag from bronze config
        save_json = bronze_config.get("save_json", False)
        if save_json:
            logger.info("JSON export enabled for Bronze layer")

        storage = StorageAdapter(
            BronzeWriter(
                bucket=bronze_path,
                endpoint_url=aws_config.endpoint_url if not is_local_run else None,
                access_key=access_key,
                secret_key=secret_key,
                save_json=save_json,
                json_path=json_path,
            ),
            DeltaWriter(
                base_path=silver_base_path,
                storage_options=storage_options,
                csv_path=csv_path,
            ),
            GoldWriter(
                base_path=gold_base_path,
                storage_options=storage_options,
                csv_path=csv_path,
            ),
        )

        lock: LockPort
        if settings.env == "prod":
            logger.info("Using RedisDistributedLock for production environment.")
            redis_client = create_redis_client(settings)
            lock = RedisDistributedLock(redis_client=redis_client)
        else:
            logger.warning("Using MemoryLock. Locking is NOT distributed. Suitable for dev/testing only.")
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
    ) -> "ChEMBLActivityPipeline":
        """Creates ChEMBL Activity pipeline with decomposed config."""
        from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=settings, logger=logger, **kwargs
        )

        return ChEMBLActivityPipeline.create(
            runtime=runtime,
            services=services,
            config=CHEMBL_ACTIVITY_CONFIG,
        )
