"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from typing import Any

from bioetl.application.pipeline.base import BasePipeline
from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import Watermark


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data.

    Transforms raw ChEMBL activity records into normalized format:
    - Bronze: Raw JSON from ChEMBL API
    - Silver: Normalized with entity_id, content_hash, metadata
    - Gold: Filtered high-quality activities (optional)

    Example:
        >>> from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
        >>> from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
        >>> # ... initialize adapters
        >>> pipeline = ChEMBLActivityPipeline(
        ...     run_type=RunType.INCREMENTAL,
        ...     data_source=chembl_adapter,
        ...     storage=storage_adapter,
        ...     lock=redis_lock,
        ...     checkpoint=s3_checkpoint,
        ...     quarantine=quarantine,
        ... )
        >>> await pipeline.run()
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize ChEMBL Activity pipeline."""
        super().__init__(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            *args,
            **kwargs,
        )

    async def transform_bronze_to_silver(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform raw ChEMBL activity to normalized format.

        Args:
            record: Raw activity record from ChEMBL

        Returns:
            Normalized record or None if should skip

        Transformation logic:
        1. Generate stable entity_id from activity_id
        2. Extract key fields (molecule, target, assay)
        3. Normalize units and values
        4. Generate content_hash for deduplication
        5. Add metadata fields
        """
        # Skip if missing critical fields
        if not record.get("activity_id"):
            return None

        # Extract core fields
        activity_id = str(record["activity_id"])
        molecule_chembl_id = record.get("molecule_chembl_id")
        target_chembl_id = record.get("target_chembl_id")
        assay_chembl_id = record.get("assay_chembl_id")

        # Generate entity_id (stable identifier)
        entity_id = generate_entity_id(
            record={"activity_id": activity_id},
            provider=self.provider,
            business_key="activity_id",
        )

        # Extract measurement data
        standard_type = record.get("standard_type")  # IC50, Ki, EC50, etc.
        standard_value = record.get("standard_value")
        standard_units = record.get("standard_units")
        standard_relation = record.get("standard_relation")  # =, <, >, ~

        # Convert value to float if present
        if standard_value is not None:
            try:
                standard_value = float(standard_value)
            except (ValueError, TypeError):
                standard_value = None

        # Extract assay information
        assay_type = record.get("assay_type")
        assay_description = record.get("assay_description")

        # Extract publication info
        document_chembl_id = record.get("document_chembl_id")
        document_year = record.get("document_year")

        # Build normalized record
        normalized = {
            "entity_id": entity_id,
            "activity_id": activity_id,
            "molecule_chembl_id": molecule_chembl_id,
            "target_chembl_id": target_chembl_id,
            "assay_chembl_id": assay_chembl_id,
            "standard_type": standard_type,
            "standard_value": standard_value,
            "standard_units": standard_units,
            "standard_relation": standard_relation,
            "assay_type": assay_type,
            "assay_description": assay_description,
            "document_chembl_id": document_chembl_id,
            "document_year": document_year,
            # Additional fields
            "pchembl_value": record.get(
                "pchembl_value"
            ),  # -log10(molar IC50, XC50, etc)
            "activity_comment": record.get("activity_comment"),
            "data_validity_comment": record.get("data_validity_comment"),
        }

        # Generate content_hash for versioning
        content_hash = generate_content_hash(normalized, self.provider)
        normalized["content_hash"] = content_hash

        return normalized

    def should_write_gold(self, record: dict[str, Any]) -> bool:
        """Filter records for Gold layer.

        Gold layer criteria:
        - Must have standard_value (not null)
        - Must have standard_units
        - Must have target_chembl_id
        - Preferred standard_types: IC50, Ki, EC50, Kd
        - No data validity issues

        Args:
            record: Silver record

        Returns:
            True if passes quality filters
        """
        # Must have measurement value
        if record.get("standard_value") is None:
            return False

        # Must have units
        if not record.get("standard_units"):
            return False

        # Must have target
        if not record.get("target_chembl_id"):
            return False

        # Prefer certain measurement types
        standard_type = record.get("standard_type")
        preferred_types = {"IC50", "Ki", "EC50", "Kd", "AC50", "GI50"}

        if standard_type not in preferred_types:
            return False

        # Exclude if data validity issues
        if record.get("data_validity_comment"):
            return False

        return True

    def extract_watermark(self, record: dict[str, Any]) -> Watermark:
        """Extract watermark from record.

        Uses activity_id as watermark for incremental loading.

        Args:
            record: Activity record

        Returns:
            Watermark (activity_id)
        """
        activity_id = record.get("activity_id")
        if activity_id:
            return Watermark(str(activity_id))

        # Fallback to timestamp
        from datetime import datetime

        return Watermark(datetime.utcnow())


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines.

    Simplifies pipeline instantiation by handling adapter initialization.

    Example:
        >>> factory = ChEMBLActivityPipelineFactory()
        >>> pipeline = await factory.create(
        ...     run_type=RunType.INCREMENTAL,
        ...     resume=False,
        ... )
        >>> await pipeline.run()
    """

    @staticmethod
    async def create(
        run_type: Any,  # RunType
        resume: bool = False,
        # Adapter configurations
        chembl_url: str = "https://www.ebi.ac.uk/chembl/api/data",
        s3_bucket_bronze: str = "bioetl-bronze",
        s3_bucket_silver: str = "bioetl-silver",
        s3_bucket_checkpoints: str = "bioetl-checkpoints",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        # S3/MinIO config
        aws_endpoint_url: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
    ) -> ChEMBLActivityPipeline:
        """Create configured ChEMBL Activity pipeline.

        Args:
            run_type: Type of run (incremental, backfill, rebuild)
            resume: Resume from checkpoint if available
            chembl_url: ChEMBL API base URL
            s3_bucket_bronze: Bronze bucket name
            s3_bucket_silver: Silver bucket name
            s3_bucket_checkpoints: Checkpoints bucket name
            redis_host: Redis host
            redis_port: Redis port
            aws_endpoint_url: S3 endpoint (for MinIO)
            aws_access_key: AWS access key
            aws_secret_key: AWS secret key

        Returns:
            Configured pipeline instance
        """
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
        import redis.asyncio as aioredis

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

        # Create pipeline
        return ChEMBLActivityPipeline(
            run_type=run_type,
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            resume=resume,
        )
