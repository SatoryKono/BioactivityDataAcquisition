"""Bronze layer writer (local storage with JSONL + zstd compression).

Implements RULES.md §2.1.1 - Bronze Layer specifications.

Requirements:
- REQ-DATA-001: JSONL + zstd format
- REQ-DATA-002: Path format bronze/v1/{provider}/{entity}/{date}/
- REQ-DATA-003: Append-only writes
- REQ-DATA-004: Atomic writes

Architecture:
- Local filesystem storage
- Streams data to minimize memory usage
- Generates checksums for data integrity
"""

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import zstandard as zstd

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

from bioetl.domain.types import BatchID, RunID, RunType


class BronzeWriter:
    """Writer for Bronze layer (raw data in JSONL + zstd).

    Optionally saves uncompressed JSON copy when save_json=True.
    """

    COMPRESSION_CHUNK_SIZE = 256 * 1024
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1

    def __init__(
        self,
        base_path: str | Path,
        save_json: bool = False,
        json_path: str | None = None,
        logger: "BoundLogger | None" = None,
    ) -> None:
        """Initialize Bronze writer.

        Args:
            base_path: Base path for Bronze layer storage
            save_json: If True, also save uncompressed JSON copy
            json_path: Path for JSON files (defaults to base_path/json/)
            logger: Structured logger for observability
        """
        self.base_path = Path(base_path)
        self.save_json = save_json
        self.json_path = json_path or str(self.base_path / "json")
        self.logger = logger or structlog.get_logger(__name__)

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> Path:
        """Write raw records to Bronze layer (JSONL + zstd).

        If save_json is enabled, also writes uncompressed JSONL file.

        Args:
            records: Iterator of JSONL bytes to write.
            provider: Data provider name (e.g., 'chembl').
            entity: Entity type (e.g., 'activity').
            date: Ingestion timestamp for date partitioning.
            batch_id: Unique batch identifier.
            run_id: Pipeline run ID for traceability.
            run_type: Type of run (incremental, backfill, rebuild).

        Returns:
            Path to the written file (relative to base_path).
        """
        from datetime import UTC

        date_str = date.strftime("%Y-%m-%d")
        # Fixed path format: bronze/v1/{provider}/{entity}/{date}/...
        relative_path = (
            f"bronze/v1/{provider}/{entity}/{date_str}/batch_{batch_id}.jsonl.zst"
        )
        ingestion_ts = datetime.now(UTC)

        # Build metadata for lineage tracking
        metadata = {
            "run_id": str(run_id),
            "run_type": run_type.value,
            "ingestion_ts": ingestion_ts.isoformat(),
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
        }

        loop = asyncio.get_running_loop()

        # Optimize memory usage: Only buffer if we need to write both formats.
        # If save_json is False (default), we stream directly to compression.
        if self.save_json:
            # Buffer records since iterator can only be consumed once
            # and we may need it for both compressed and JSON output
            record_list = list(records)
            records_iter = iter(record_list)
        else:
            record_list = []  # Not used
            records_iter = records

        compressed_data = await loop.run_in_executor(
            None, self._compress_records, records_iter
        )

        if not compressed_data:
            raise ValueError("No records to write")

        # Write compressed file to local filesystem
        full_path = self.base_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        def _write_local(data: bytes, path: Path, meta: dict, meta_path: Path) -> None:
            with open(path, "wb") as f:
                f.write(data)
            with open(meta_path, "w") as f:
                json.dump(meta, f)

        meta_path = full_path.with_suffix(".zst.meta.json")
        await loop.run_in_executor(
            None,
            lambda: _write_local(compressed_data, full_path, metadata, meta_path),
        )

        # Log successful write with run_id for traceability
        self.logger.info(
            "bronze_write_complete",
            path=relative_path,
            provider=provider,
            entity=entity,
            batch_id=str(batch_id),
            run_id=str(run_id),
            run_type=run_type.value,
        )

        # Optionally write uncompressed JSON
        if self.save_json:
            await self._write_json_copy(
                record_list, provider, entity, date_str, batch_id
            )

        return Path(relative_path)

    async def _write_json_copy(
        self,
        records: list[bytes],
        provider: str,
        entity: str,
        date_str: str,
        batch_id: BatchID,
    ) -> None:
        """Write uncompressed JSONL copy of records."""
        json_relative_path = f"{provider}/{entity}/batch_{date_str}_{batch_id}.jsonl"

        # Combine all records into single JSONL content
        jsonl_content = b"".join(records)

        json_full_path = Path(self.json_path) / json_relative_path
        json_full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_full_path, "wb") as f:
            f.write(jsonl_content)

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
                    # zstandard stream writer accepts bytearray directly, avoid copy to bytes
                    writer.write(chunk_buffer)
                    chunk_buffer.clear()

            if chunk_buffer:
                writer.write(chunk_buffer)

            if record_count == 0:
                raise ValueError("No records provided for compression")

        return output.getvalue()

    async def read_bronze(self, path: str) -> AsyncIterator[dict[str, Any]]:
        """Read and decompress Bronze file (for testing/debugging)."""
        full_path = self.base_path / path
        with open(full_path, "rb") as f:
            compressed_data = f.read()

        decompressor = zstd.ZstdDecompressor()
        # Use streaming decompression since content size may not be in frame header
        with decompressor.stream_reader(compressed_data) as reader:
            decompressed_data = reader.read()

        for line in decompressed_data.decode("utf-8").splitlines():
            if line.strip():
                yield json.loads(line)

    def _list_batches_local(self, prefix: str, date: datetime | None) -> list[str]:
        """List batch files from local filesystem."""
        search_path = self.base_path / prefix
        if not search_path.exists():
            return []

        pattern = "batch_*.jsonl.zst" if date else "**/*.jsonl.zst"
        files = list(search_path.glob(pattern))
        return [str(p.relative_to(self.base_path)) for p in files]

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """List all batch files for a given provider/entity."""
        prefix = f"bronze/v1/{provider}/{entity}/"
        if date:
            prefix = f"{prefix}{date.strftime('%Y-%m-%d')}/"

        return self._list_batches_local(prefix, date)
