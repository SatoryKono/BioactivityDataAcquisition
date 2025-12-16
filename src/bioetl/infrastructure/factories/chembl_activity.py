"""ChEMBL Activity Pipeline factory.

Handles infrastructure wiring for ChEMBL Activity pipeline.
"""

from typing import Any

from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold."""

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: DeltaWriter,
        gold_writer: DeltaWriter,
    ):
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

    def write_bronze(self, *args: Any, **kwargs: Any) -> Any:
        return self.bronze.write_bronze(*args, **kwargs)

    def write_silver(self, *args: Any, **kwargs: Any) -> None:
        return self.silver.write_silver(*args, **kwargs)

    def write_gold(self, *args: Any, **kwargs: Any) -> None:
        return self.gold.write_gold(*args, **kwargs)


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines.

    Simplifies pipeline instantiation by handling adapter initialization.
    """

    @staticmethod
    async def create(
        run_type: Any,
        resume: bool = False,
        s3_bucket_bronze: str = "bioetl-bronze",
        s3_bucket_silver: str = "bioetl-silver",
        s3_bucket_checkpoints: str = "bioetl-checkpoints",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        aws_endpoint_url: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
    ) -> ChEMBLActivityPipeline:
        """Create configured ChEMBL Activity pipeline."""
        import redis.asyncio as aioredis

        storage_options = {
            "AWS_ENDPOINT_URL": aws_endpoint_url,
            "AWS_ACCESS_KEY_ID": aws_access_key,
            "AWS_SECRET_ACCESS_KEY": aws_secret_key,
        }

        bucket = TokenBucket(rate=10.0, capacity=20)
        circuit_breaker = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, circuit_breaker)
        data_source = ChemblAdapter(http_client=http_client)

        bronze_writer = BronzeWriter(
            bucket=s3_bucket_bronze,
            endpoint_url=aws_endpoint_url,
            access_key=aws_access_key,
            secret_key=aws_secret_key,
        )
        silver_writer = DeltaWriter(
            base_path=f"s3://{s3_bucket_silver}",
            storage_options=storage_options if aws_endpoint_url else None,
        )
        gold_writer = DeltaWriter(
            base_path=f"s3://{s3_bucket_silver}",
            storage_options=storage_options if aws_endpoint_url else None,
        )
        storage = StorageAdapter(bronze_writer, silver_writer, gold_writer)

        redis_client = aioredis.Redis(host=redis_host, port=redis_port)
        lock = RedisDistributedLock(redis_client=redis_client)

        checkpoint = S3Checkpoint(
            bucket=s3_bucket_checkpoints,
            endpoint_url=aws_endpoint_url,
            access_key=aws_access_key,
            secret_key=aws_secret_key,
        )

        quarantine = UnifiedQuarantine(
            base_path=f"s3://{s3_bucket_silver}/common/quarantine",
            storage_options=storage_options if aws_endpoint_url else None,
        )

        return ChEMBLActivityPipeline(
            run_type=run_type,
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            resume=resume,
        )
