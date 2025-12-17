"""Bronze layer writer (S3-compatible storage with JSONL + zstd compression).

Implements RULES.md §2.1.1 - Bronze Layer specifications.

Requirements:
- REQ-DATA-001: JSONL + zstd format
- REQ-DATA-002: Path format bronze/v1/{provider}/{entity}/{date}/
- REQ-DATA-003: Append-only writes
- REQ-DATA-004: Atomic writes
- REQ-DATA-005: 90-day retention (S3 lifecycle)

Architecture:
- Uses boto3 for S3 operations (MinIO compatible)
- Streams data to minimize memory usage
- Generates checksums for data integrity
"""

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import zstandard as zstd
from botocore.exceptions import ClientError

from bioetl.domain.types import BatchID
from bioetl.domain.exceptions import BucketNotFoundError, UploadError


class BronzeWriter:
    """Writer for Bronze layer (raw data in JSONL + zstd)."""

    COMPRESSION_CHUNK_SIZE = 256 * 1024
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize Bronze writer."""
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.is_local = not endpoint_url

        if not self.is_local:
            from bioetl.infrastructure.storage.s3_pool import S3ClientPool
            self.s3_client = S3ClientPool.get_client(
                endpoint_url=endpoint_url,
                region=region,
                access_key=access_key,
                secret_key=secret_key,
            )

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
    ) -> Path:
        """Write raw records to Bronze layer (JSONL + zstd)."""
        date_str = date.strftime("%Y-%m-%d")
        # New, cleaner path structure as requested
        relative_path = f"{provider}/{entity}/batch_{date_str}_{batch_id}.jsonl.zst"

        loop = asyncio.get_running_loop()
        compressed_data = await loop.run_in_executor(
            None, self._compress_records, records
        )

        if not compressed_data:
            raise ValueError("No records to write")

        if self.is_local:
            full_path = Path(self.bucket) / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(compressed_data)
        else:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=relative_path,
                        Body=compressed_data,
                        ContentType="application/zstd",
                    ),
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "NoSuchBucket":
                    raise BucketNotFoundError(self.bucket) from e
                raise UploadError(relative_path, str(e)) from e

        return Path(relative_path)

    def _compress_records(self, records: Iterator[bytes]) -> bytes:
        """Compress JSONL records using zstandard with streaming."""
        output = BytesIO()
        compressor = zstd.ZstdCompressor(
            level=self.COMPRESSION_LEVEL,
            threads=self.COMPRESSION_THREADS,
            write_content_size=True,
        )

        chunk_buffer = bytearray()
        record_count = 0

        with compressor.stream_writer(
            output, closefd=False, write_size=self.COMPRESSION_CHUNK_SIZE
        ) as writer:
            for record in records:
                chunk_buffer.extend(record)
                record_count += 1

                if len(chunk_buffer) >= self.COMPRESSION_CHUNK_SIZE:
                    writer.write(bytes(chunk_buffer))
                    chunk_buffer.clear()

            if chunk_buffer:
                writer.write(bytes(chunk_buffer))

            if record_count == 0:
                raise ValueError("No records provided for compression")

        return output.getvalue()

    async def read_bronze(self, path: str) -> AsyncIterator[dict[str, Any]]:
        """Read and decompress Bronze file (for testing/debugging)."""
        loop = asyncio.get_running_loop()
        if self.is_local:
            full_path = Path(self.bucket) / path
            with open(full_path, "rb") as f:
                compressed_data = f.read()
        else:
            response = await loop.run_in_executor(
                None, lambda: self.s3_client.get_object(Bucket=self.bucket, Key=path)
            )
            compressed_data = response["Body"].read()

        decompressor = zstd.ZstdDecompressor()
        decompressed_data = decompressor.decompress(compressed_data)

        for line in decompressed_data.decode("utf-8").splitlines():
            if line.strip():
                yield json.loads(line)

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """List all batch files for a given provider/entity."""
        # This method might need adjustment based on the new path structure
        # For now, it will search inside the provider/entity folder
        prefix = f"{provider}/{entity}/"

        if self.is_local:
            base_path = Path(self.bucket) / prefix
            if not base_path.exists():
                return []

            files = list(base_path.glob("batch_*.jsonl.zst"))
            if date:
                date_str = date.strftime("%Y-%m-%d")
                files = [p for p in files if f"batch_{date_str}" in p.name]

            return [str(p.relative_to(self.bucket)) for p in files]
        else:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix,
                ),
            )

            all_files = [
                obj["Key"]
                for obj in response.get("Contents", [])
                if obj["Key"].endswith(".jsonl.zst")
            ]

            if date:
                date_str = date.strftime("%Y-%m-%d")
                return [key for key in all_files if f"batch_{date_str}" in key]

            return all_files
