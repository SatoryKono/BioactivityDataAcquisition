"""S3-based checkpoint storage with atomic writes.

Implements RULES.md §5.3.1 - Checkpoint Recovery.

Requirements:
- REQ-CHECKPOINT-001: Check existence on startup
- REQ-CHECKPOINT-002: Atomic writes (If-Match/ETag)
- REQ-CHECKPOINT-003: Recovery on --resume flag
- REQ-CHECKPOINT-004: Delete after successful run
- REQ-SHUTDOWN-003: Atomic save with If-Match/ETag

Architecture:
- Uses S3 ETags for optimistic concurrency control
- Stores checkpoints as JSON in S3
- Path: s3://{bucket}/checkpoints/{pipeline}/latest.json
- Metadata includes watermark, run_id, and custom metadata
"""

import json
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from bioetl.domain.types import RunID, Watermark


class S3Checkpoint:
    """Checkpoint storage using S3 with atomic writes.

    Implements CheckpointPort interface from domain/ports.py.

    Example:
        >>> checkpoint = S3Checkpoint(
        ...     bucket="bioetl-checkpoints",
        ...     endpoint_url="http://localhost:9000",
        ...     access_key="bioetl",
        ...     secret_key="bioetl_minio_pass"
        ... )
        >>> from datetime import datetime
        >>> run_id = RunID(UUID("12345678-1234-1234-1234-123456789abc"))
        >>> checkpoint.save(
        ...     pipeline="chembl_activity",
        ...     watermark=Watermark(datetime(2025, 12, 15)),
        ...     run_id=run_id,
        ...     metadata={"records_processed": 1000}
        ... )
        >>> loaded = checkpoint.load("chembl_activity")
        >>> if loaded:
        ...     watermark, run_id, metadata = loaded
        ...     print(f"Resume from {watermark}")
    """

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize S3 checkpoint storage.

        Args:
            bucket: S3 bucket name (e.g., 'bioetl-checkpoints')
            endpoint_url: S3 endpoint URL (for MinIO)
            region: AWS region
            access_key: AWS access key (optional, uses env vars if None)
            secret_key: AWS secret key (optional, uses env vars if None)
        """
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

        self.s3_client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            config=boto3.session.Config(signature_version="s3v4"),
        )
        self.bucket = bucket

    def save(
        self,
        pipeline: str,
        watermark: Watermark,
        run_id: RunID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save checkpoint atomically.

        Requirements:
        - REQ-SHUTDOWN-003: Atomic save with If-Match/ETag

        Uses S3 ETags for optimistic concurrency control:
        1. Load current checkpoint (if exists) to get ETag
        2. Write new checkpoint with If-Match condition
        3. If ETag changed, write fails (another process updated it)

        Args:
            pipeline: Pipeline name (e.g., 'chembl_activity')
            watermark: Checkpoint value (timestamp, ID, or offset)
            run_id: Current run ID
            metadata: Optional metadata (e.g., records_processed, last_batch_id)

        Raises:
            CheckpointConflictError: If checkpoint was modified by another process
            ClientError: S3 errors
        """
        s3_key = self._get_key(pipeline)

        # Serialize watermark (handle datetime, int, str)
        if isinstance(watermark, (int, str)):
            watermark_str = str(watermark)
        else:
            # Assume datetime-like
            watermark_str = watermark.isoformat()

        # Prepare checkpoint data
        checkpoint_data = {
            "pipeline": pipeline,
            "watermark": watermark_str,
            "run_id": str(run_id),
            "metadata": metadata or {},
            "version": "1.0",
        }

        # Serialize to JSON
        checkpoint_json = json.dumps(checkpoint_data, indent=2)

        # Get current ETag if checkpoint exists
        current_etag = self._get_etag(s3_key)

        try:
            # Atomic write with If-Match condition
            put_kwargs: dict[str, Any] = {
                "Bucket": self.bucket,
                "Key": s3_key,
                "Body": checkpoint_json.encode("utf-8"),
                "ContentType": "application/json",
                "Metadata": {
                    "pipeline": pipeline,
                    "run_id": str(run_id),
                },
            }

            if current_etag:
                # Checkpoint exists, use If-Match for atomicity
                put_kwargs["IfMatch"] = current_etag

            self.s3_client.put_object(**put_kwargs)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "PreconditionFailed":
                # ETag mismatch - checkpoint was modified by another process
                raise CheckpointConflictError(
                    pipeline,
                    "Checkpoint was modified by another process",
                ) from e
            raise

    def load(self, pipeline: str) -> tuple[Watermark, RunID, dict[str, Any]] | None:
        """Load last checkpoint.

        Requirements:
        - REQ-CHECKPOINT-001: Check existence on startup

        Args:
            pipeline: Pipeline name

        Returns:
            Tuple of (watermark, run_id, metadata) if checkpoint exists,
            None otherwise

        Example:
            >>> checkpoint = S3Checkpoint(bucket="bioetl-checkpoints")
            >>> result = checkpoint.load("chembl_activity")
            >>> if result:
            ...     watermark, run_id, metadata = result
            ...     print(f"Resume from {watermark}")
            ... else:
            ...     print("No checkpoint found, starting fresh")
        """
        s3_key = self._get_key(pipeline)

        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            checkpoint_json = response["Body"].read().decode("utf-8")
            checkpoint_data = json.loads(checkpoint_json)

            # Parse watermark (try different types)
            watermark_str = checkpoint_data["watermark"]
            try:
                # Try as datetime
                from datetime import datetime

                watermark = Watermark(datetime.fromisoformat(watermark_str))
            except (ValueError, TypeError):
                # Try as int
                try:
                    watermark = Watermark(int(watermark_str))
                except ValueError:
                    # Use as string
                    watermark = Watermark(watermark_str)

            # Parse run_id
            run_id = RunID(UUID(checkpoint_data["run_id"]))

            # Get metadata
            metadata = checkpoint_data.get("metadata", {})

            return (watermark, run_id, metadata)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                # Checkpoint doesn't exist
                return None
            raise

    def delete(self, pipeline: str) -> None:
        """Delete checkpoint (after successful run).

        Requirements:
        - REQ-CHECKPOINT-004: Delete after success

        Args:
            pipeline: Pipeline name

        Note:
            Does not raise error if checkpoint doesn't exist.
        """
        s3_key = self._get_key(pipeline)

        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code != "NoSuchKey":
                # Ignore if key doesn't exist, raise for other errors
                raise

    def exists(self, pipeline: str) -> bool:
        """Check if checkpoint exists.

        Args:
            pipeline: Pipeline name

        Returns:
            True if checkpoint exists, False otherwise
        """
        s3_key = self._get_key(pipeline)

        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                return False
            raise

    def list_all(self) -> list[str]:
        """List all checkpoint pipelines.

        Returns:
            List of pipeline names that have checkpoints

        Example:
            >>> checkpoint = S3Checkpoint(bucket="bioetl-checkpoints")
            >>> pipelines = checkpoint.list_all()
            >>> print(f"Found checkpoints for: {', '.join(pipelines)}")
        """
        prefix = "checkpoints/"

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            )

            pipelines = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/latest.json"):
                    # Extract pipeline name from path
                    # Format: checkpoints/{pipeline}/latest.json
                    pipeline = key.replace(prefix, "").replace("/latest.json", "")
                    pipelines.append(pipeline)

            return pipelines

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                return []
            raise

    def _get_key(self, pipeline: str) -> str:
        """Generate S3 key for checkpoint.

        Args:
            pipeline: Pipeline name

        Returns:
            S3 key (e.g., 'checkpoints/chembl_activity/latest.json')
        """
        return f"checkpoints/{pipeline}/latest.json"

    def _get_etag(self, s3_key: str) -> str | None:
        """Get current ETag for a checkpoint.

        Args:
            s3_key: S3 key

        Returns:
            ETag string if object exists, None otherwise
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return response["ETag"].strip('"')  # Remove quotes from ETag
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                return None
            raise


class CheckpointConflictError(Exception):
    """Raised when checkpoint write fails due to concurrent modification."""

    def __init__(self, pipeline: str, message: str) -> None:
        """Initialize error.

        Args:
            pipeline: Pipeline name
            message: Error message
        """
        self.pipeline = pipeline
        super().__init__(f"Checkpoint conflict for pipeline '{pipeline}': {message}")
