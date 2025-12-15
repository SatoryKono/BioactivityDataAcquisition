"""Bootstrap module for BioETL.

Handles dependency injection, configuration loading, and object graph wiring.
This module is the "Main Component" in Clean Architecture terms, responsible
for assembling the system.
"""

from __future__ import annotations

import os
from typing import Any

from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.domain.types import RunType


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines.

    Simplifies pipeline instantiation by handling adapter initialization.
    Moved from application layer to bootstrap to enforce dependency rules.
    """

    @staticmethod
    async def create(
        run_type: RunType,
        resume: bool = False,
        limit: int | None = None,
    ) -> ChEMBLActivityPipeline:
        """Create configured ChEMBL Activity pipeline.

        Args:
            run_type: Type of run (incremental, backfill, rebuild)
            resume: Resume from checkpoint if available
            limit: Execution limit (optional)

        Returns:
            Configured pipeline instance
        """
        # Infrastructure imports are allowed here (in Main/Bootstrap)
        import redis.asyncio as aioredis

        from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
        from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
        from bioetl.infrastructure.quarantine.unified_quarantine import (
            UnifiedQuarantine,
        )
        from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        from bioetl.config import settings

        # Load configuration from typed settings
        aws_endpoint_url = settings.AWS_ENDPOINT_URL
        aws_access_key = settings.AWS_ACCESS_KEY_ID
        aws_secret_key = settings.AWS_SECRET_ACCESS_KEY.get_secret_value() if settings.AWS_SECRET_ACCESS_KEY else None

        s3_bucket_bronze = settings.BIOETL_S3_BUCKET_BRONZE
        s3_bucket_silver = settings.BIOETL_S3_BUCKET_SILVER
        s3_bucket_checkpoints = settings.BIOETL_S3_BUCKET_CHECKPOINTS

        redis_host = settings.BIOETL_REDIS_HOST
        redis_port = settings.BIOETL_REDIS_PORT

        # Create storage adapter wrapper
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

        # Initialize adapters
        storage_options = {
            "AWS_ENDPOINT_URL": aws_endpoint_url,
            "AWS_ACCESS_KEY_ID": aws_access_key,
            "AWS_SECRET_ACCESS_KEY": aws_secret_key,
        }

        # Data source (ChEMBL)
        bucket = TokenBucket(rate=10.0, capacity=20)
        circuit_breaker = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, circuit_breaker)
        data_source = ChemblAdapter(http_client=http_client)

        # Storage
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
            base_path=f"s3://{s3_bucket_silver}",  # Same bucket, different tables
            storage_options=storage_options if aws_endpoint_url else None,
        )
        storage = StorageAdapter(bronze_writer, silver_writer, gold_writer)

        # Lock (Redis)
        redis_client = aioredis.Redis(host=redis_host, port=redis_port)
        lock = RedisDistributedLock(redis_client=redis_client)

        # Checkpoint (S3)
        checkpoint = S3Checkpoint(
            bucket=s3_bucket_checkpoints,
            endpoint_url=aws_endpoint_url,
            access_key=aws_access_key,
            secret_key=aws_secret_key,
        )

        # Quarantine
        quarantine = UnifiedQuarantine(
            base_path=f"s3://{s3_bucket_silver}/common/quarantine",
            storage_options=storage_options if aws_endpoint_url else None,
        )

        # Configure logging
        # This restores structured logging configuration that might have been lost
        # when removing infrastructure imports from application layer.
        from bioetl.infrastructure.observability.logging import configure_logging

        # We use a default run_id for bootstrap, but the pipeline will generate its own.
        # Ideally, we should pass a run_id to the factory if we want to trace initialization.
        configure_logging(log_level=settings.LOG_LEVEL, json_format=settings.LOG_FORMAT_JSON)

        # Create pipeline
        pipeline = ChEMBLActivityPipeline(
            run_type=run_type,
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            resume=resume,
        )

        # Handle limit by wrapping data source fetch if needed, or setting it on pipeline
        # Since BasePipeline doesn't have an explicit 'limit' arg in __init__ but
        # data_source.fetch() supports it, we can't easily bake it into the object graph
        # unless we wrap the data source or the pipeline handles it.
        #
        # BasePipeline._extract() calls self.data_source.fetch(watermark=watermark).
        # It doesn't pass limit.
        #
        # To support limit without changing BasePipeline signature (which might be frozen for this task),
        # we can wrap the data source.

        if limit is not None:
            original_fetch = data_source.fetch

            async def limited_fetch(entity_type, watermark=None, limit=limit):
                # We ignore the limit passed by caller (if any) and enforce the factory limit
                # Or we use the smaller of the two.
                # Here we just pass the configured limit.
                async for record in original_fetch(entity_type, watermark, limit=limit):
                    yield record

            # Patch the instance method - a bit dirty but effective for bootstrap wiring
            # without changing the class hierarchy.
            # A cleaner way would be a LimitingDataSourceDecorator.
            data_source.fetch = limited_fetch # type: ignore

        return pipeline
