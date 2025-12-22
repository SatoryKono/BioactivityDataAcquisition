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

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from botocore.exceptions import ClientError

from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.types import RunID, Watermark


class S3Checkpoint:
    """Checkpoint storage using S3 with atomic writes.

    Implements CheckpointPort interface from domain/ports.py.
    """

    def __init__(
        self,
        bucket: str,
        pipeline_name: str | None = None,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize S3 checkpoint storage."""
        self.bucket = bucket
        self.pipeline_name = pipeline_name  # Unused but kept for interface compatibility
        self.endpoint_url = endpoint_url
        self.is_local = not endpoint_url

        # Check if we are in test mode with local paths masquerading as buckets
        if bucket.startswith("/") or bucket.startswith("."):
            self.is_local = True

        if not self.is_local:
            from bioetl.infrastructure.storage.s3_pool import S3ClientPool

            self.s3_client = S3ClientPool.get_client(
                endpoint_url=endpoint_url,
                region=region,
                access_key=access_key,
                secret_key=secret_key,
            )

    async def save(
        self,
        pipeline: str,
        watermark: Watermark,
        run_id: RunID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save checkpoint atomically."""
        key = self._get_key(pipeline)

        watermark_str = watermark.to_api_param()

        checkpoint_data = {
            "pipeline": pipeline,
            "watermark": watermark_str,
            "run_id": str(run_id),
            "metadata": metadata or {},
            "version": "1.0",
        }
        checkpoint_json = json.dumps(checkpoint_data, indent=2)

        if self.is_local:
            full_path = Path(self.bucket) / key
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(checkpoint_json)
        else:
            loop = asyncio.get_running_loop()
            current_etag = await self._get_etag(key)
            try:
                put_kwargs: dict[str, Any] = {
                    "Bucket": self.bucket,
                    "Key": key,
                    "Body": checkpoint_json.encode("utf-8"),
                    "ContentType": "application/json",
                }
                if current_etag:
                    put_kwargs["IfMatch"] = current_etag
                await loop.run_in_executor(
                    None, lambda: self.s3_client.put_object(**put_kwargs)
                )
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") == "PreconditionFailed":
                    raise CheckpointConflictError(
                        pipeline, "Checkpoint was modified"
                    ) from e
                raise

    async def load(
        self, pipeline: str
    ) -> tuple[Watermark, RunID, dict[str, Any]] | None:
        """Load last checkpoint."""
        key = self._get_key(pipeline)

        if self.is_local:
            full_path = Path(self.bucket) / key
            if not full_path.exists():
                return None
            with open(full_path) as f:
                checkpoint_json = f.read()
        else:
            loop = asyncio.get_running_loop()
            try:
                response = await loop.run_in_executor(
                    None, lambda: self.s3_client.get_object(Bucket=self.bucket, Key=key)
                )
                checkpoint_json = response["Body"].read().decode("utf-8")
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                    return None
                raise

        checkpoint_data = json.loads(checkpoint_json)
        watermark_str = checkpoint_data["watermark"]

        # Determine type and wrap in Watermark object
        value: Any
        try:
            from datetime import datetime

            value = datetime.fromisoformat(watermark_str)
            watermark = Watermark.from_timestamp(value)
        except (ValueError, TypeError):
            try:
                value = int(watermark_str)
                watermark = Watermark.from_offset(value)
            except ValueError:
                value = watermark_str
                watermark = Watermark.from_id(value)

        run_id = RunID(UUID(checkpoint_data["run_id"]))
        metadata = checkpoint_data.get("metadata", {})
        return (watermark, run_id, metadata)

    async def delete(self, pipeline: str) -> None:
        """Delete checkpoint."""
        key = self._get_key(pipeline)
        if self.is_local:
            full_path = Path(self.bucket) / key
            if full_path.exists():
                full_path.unlink()
        else:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.delete_object(Bucket=self.bucket, Key=key),
                )
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                    raise

    async def list_all(self) -> list[str]:
        """List all pipelines with checkpoints."""
        prefix = "checkpoints/"
        pipelines = set()
        if self.is_local:
            root = Path(self.bucket) / prefix
            if root.exists():
                for path in root.iterdir():
                    if path.is_dir():
                        pipelines.add(path.name)
        else:
            loop = asyncio.get_running_loop()
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = await loop.run_in_executor(
                None,
                lambda: paginator.paginate(
                    Bucket=self.bucket, Prefix=prefix, Delimiter="/"
                ),
            )
            for page in pages:
                for common_prefix in page.get("CommonPrefixes", []):
                    pipeline_name = (
                        common_prefix.get("Prefix", "").removeprefix(prefix).strip("/")
                    )
                    if pipeline_name:
                        pipelines.add(pipeline_name)
        return sorted(list(pipelines))

    async def exists(self, pipeline: str) -> bool:
        """Check if checkpoint exists."""
        key = self._get_key(pipeline)
        if self.is_local:
            return (Path(self.bucket) / key).exists()
        else:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.head_object(Bucket=self.bucket, Key=key),
                )
                return True
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                    return False
                raise

    def _get_key(self, pipeline: str) -> str:
        return f"checkpoints/{pipeline}/latest.json"

    async def _get_etag(self, s3_key: str) -> str | None:
        """Get current ETag for a checkpoint."""
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(Bucket=self.bucket, Key=s3_key),
            )
            return response["ETag"].strip('"')
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise

    async def aclose(self) -> None:
        pass
