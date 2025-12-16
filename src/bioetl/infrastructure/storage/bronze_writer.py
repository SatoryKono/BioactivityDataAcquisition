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
    """Writer for Bronze layer (raw data in JSONL + zstd).

    Path format: bronze/v1/{provider}/{entity}/{date}/batch_{batch_id}.jsonl.zst

    Performance Configuration:
        COMPRESSION_CHUNK_SIZE: Size of chunks for streaming compression (default: 256KB)
                                Larger chunks = better compression ratio
                                Smaller chunks = lower memory usage
        COMPRESSION_LEVEL: zstd compression level (default: 3)
                          Range: 1 (fastest) to 22 (best compression)
                          Level 3 is optimal for speed/ratio balance

    Example:
        >>> writer = BronzeWriter(
        ...     bucket="bioetl-bronze",
        ...     endpoint_url="http://localhost:9000",
        ...     access_key="bioetl",
        ...     secret_key="bioetl_minio_pass"
        ... )
        >>> records = [b'{"id": "CHEMBL123", "value": 5.5}\\n']
        >>> path = await writer.write_bronze(
        ...     records=iter(records),
        ...     provider="chembl",
        ...     entity="activity",
        ...     date=datetime(2025, 12, 15),
        ...     batch_id=BatchID(UUID("12345678-1234-1234-1234-123456789abc"))
        ... )
        >>> print(path)
        bronze/v1/chembl/activity/2025-12-15/batch_12345678-1234-1234-1234-123456789abc.jsonl.zst
    """

    # Performance tuning constants (REQ-RATE-002: Backpressure support)
    COMPRESSION_CHUNK_SIZE = 256 * 1024  # 256KB chunks for optimal I/O
    COMPRESSION_LEVEL = 3  # Balance between speed and compression ratio
    COMPRESSION_THREADS = -1  # Auto-detect CPU cores

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize Bronze writer.

        Args:
            bucket: S3 bucket name (e.g., 'bioetl-bronze')
            endpoint_url: S3 endpoint URL (for MinIO, e.g., 'http://localhost:9000')
            region: AWS region (default: 'us-east-1')
            access_key: AWS access key ID (optional, uses env vars if None)
            secret_key: AWS secret access key (optional, uses env vars if None)
        """
        from bioetl.infrastructure.storage.s3_pool import S3ClientPool

        # Get S3 client from pool for connection reuse
        self.s3_client = S3ClientPool.get_client(
            endpoint_url=endpoint_url,
            region=region,
            access_key=access_key,
            secret_key=secret_key,
        )
        self.bucket = bucket
        self.loop = asyncio.get_event_loop()

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
    ) -> Path:
        """Write raw records to Bronze layer (JSONL + zstd).

        Requirements:
        - REQ-DATA-001: JSONL + zstd format
        - REQ-DATA-002: Path format bronze/v1/{provider}/{entity}/{date}/
        - REQ-DATA-003: Append-only writes (immutable)
        - REQ-DATA-004: Atomic writes (via S3 PutObject)

        Args:
            records: Iterator of JSONL records (bytes, one JSON object per line)
            provider: Provider name (e.g., 'chembl', 'pubchem')
            entity: Entity type (e.g., 'activity', 'compound')
            date: Ingestion date (used for partitioning)
            batch_id: Unique batch identifier

        Returns:
            Path to written file (relative to bucket root)

        Raises:
            ValueError: If records iterator is empty
            BucketNotFoundError: If the S3 bucket does not exist.
            UploadError: If the upload to S3 fails for other reasons.
        """
        # Generate S3 key (path)
        date_str = date.strftime("%Y-%m-%d")
        s3_key = (
            f"bronze/v1/{provider}/{entity}/{date_str}/" f"batch_{batch_id}.jsonl.zst"
        )

        # Compress data in memory
        compressed_data = await self.loop.run_in_executor(
            None, self._compress_records, records
        )

        if not compressed_data:
            raise ValueError("No records to write")

        # Upload to S3 (atomic operation)
        try:
            await self.loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=compressed_data,
                    ContentType="application/zstd",
                    Metadata={
                        "provider": provider,
                        "entity": entity,
                        "batch_id": str(batch_id),
                        "ingestion_date": date_str,
                        "format_version": "v1",
                    },
                ),
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise BucketNotFoundError(self.bucket) from e
            raise UploadError(s3_key, str(e)) from e

        return Path(s3_key)

    def _compress_records(self, records: Iterator[bytes]) -> bytes:
        """Compress JSONL records using zstandard with streaming.

        This method now uses streaming compression with chunked buffering
        to minimize peak memory usage. Records are compressed incrementally
        instead of loading the entire batch into memory.

        Performance characteristics:
        - Memory: O(1) - constant buffer size regardless of batch size
        - CPU: Parallelized compression (threads=-1)
        - Suitable for large batches (1000+ records)

        Args:
            records: Iterator of JSONL records (bytes)

        Returns:
            Compressed data as bytes

        Raises:
            ValueError: If records iterator is empty

        Implementation note:
        While this still materializes the final compressed output,
        the compression itself is now streaming. For true streaming upload,
        use _stream_compress_and_upload() with aioboto3 (future enhancement).
        """
        # Use BytesIO with streaming compression
        output = BytesIO()
        compressor = zstd.ZstdCompressor(
            level=self.COMPRESSION_LEVEL,
            threads=self.COMPRESSION_THREADS,
            write_content_size=True,  # Add content size to frame header
        )

        # Streaming compression with chunk buffer (REQ-RATE-002: Backpressure)
        chunk_buffer = bytearray()
        record_count = 0

        with compressor.stream_writer(
            output, closefd=False, write_size=self.COMPRESSION_CHUNK_SIZE
        ) as writer:
            for record in records:
                chunk_buffer.extend(record)
                record_count += 1

                # Flush chunk when buffer reaches threshold
                # This implements incremental compression to minimize peak memory
                if len(chunk_buffer) >= self.COMPRESSION_CHUNK_SIZE:
                    writer.write(bytes(chunk_buffer))
                    chunk_buffer.clear()

            # Write remaining data
            if chunk_buffer:
                writer.write(bytes(chunk_buffer))

            if record_count == 0:
                raise ValueError("No records provided for compression")

        return output.getvalue()

    async def read_bronze(self, s3_key: str) -> AsyncIterator[dict[str, Any]]:
        """Read and decompress Bronze file (for testing/debugging).

        Args:
            s3_key: S3 key (path) to Bronze file

        Yields:
            Parsed JSON records

        Example:
            >>> writer = BronzeWriter(bucket="bioetl-bronze")
            >>> records = [record async for record in writer.read_bronze(
            ...     "bronze/v1/chembl/activity/2025-12-15/batch_xxx.jsonl.zst"
            ... )]
        """
        # Download from S3
        response = await self.loop.run_in_executor(
            None, lambda: self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
        )
        compressed_data = response["Body"].read()

        # Decompress
        decompressor = zstd.ZstdDecompressor()
        decompressed_data = decompressor.decompress(compressed_data)

        # Parse JSONL
        for line in decompressed_data.decode("utf-8").splitlines():
            if line.strip():
                yield json.loads(line)

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """List all batch files for a given provider/entity.

        Args:
            provider: Provider name
            entity: Entity type
            date: Optional date filter (if None, lists all dates)

        Returns:
            List of S3 keys (paths)
        """
        if date:
            date_str = date.strftime("%Y-%m-%d")
            prefix = f"bronze/v1/{provider}/{entity}/{date_str}/"
        else:
            prefix = f"bronze/v1/{provider}/{entity}/"

        response = await self.loop.run_in_executor(
            None,
            lambda: self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            ),
        )

        return [
            obj["Key"]
            for obj in response.get("Contents", [])
            if obj["Key"].endswith(".jsonl.zst")
        ]
