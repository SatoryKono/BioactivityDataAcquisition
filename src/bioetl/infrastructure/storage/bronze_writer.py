"""Bronze layer writer (local storage with JSONL + zstd compression).

Implements RULES.md §2.1.1 - Bronze Layer specifications.

Requirements:
- REQ-DATA-001: JSONL + zstd format
- REQ-DATA-002: Path format bronze/v1/{provider}/{entity}/{date}/
- REQ-DATA-003: Append-only writes
- REQ-DATA-004: Atomic writes (via temp file + rename)

Architecture:
- Local filesystem storage
- Streams data to minimize memory usage
- Generates checksums for data integrity
- Atomic writes using AtomicWriteGroup for data + metadata consistency
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import zstandard as zstd

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage._atomic import AtomicWriteGroup


class BronzeWriter:
    """Writer for Bronze layer (raw data in JSONL + zstd).

    Optionally saves uncompressed JSON copy when save_json=True.

    Note: LoggerPort is required per RULES.md DI requirements. All dependencies
    MUST be injected through constructor without fallback defaults.
    """

    COMPRESSION_CHUNK_SIZE = 256 * 1024
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        save_json: bool = False,
        json_path: str | None = None,
    ) -> None:
        """Initialize Bronze writer.

        Args:
            base_path: Base path for Bronze layer storage
            logger: Structured logger for observability (MUST be injected)
            save_json: If True, also save uncompressed JSON copy
            json_path: Path for JSON files (defaults to base_path/json/)

        """
        self.base_path = Path(base_path)
        self.logger = logger
        self.save_json = save_json
        self.json_path = json_path or str(self.base_path / "json")

    def _validate_bronze_names(self, provider: str, entity: str) -> None:
        """Validate provider and entity names (alphanumeric + underscores only)."""
        if not provider or not provider.replace("_", "").isalnum():
            raise ValueError(
                f"Invalid provider name: '{provider}'. "
                "Use alphanumeric characters and underscores only."
            )
        if not entity or not entity.replace("_", "").isalnum():
            raise ValueError(
                f"Invalid entity name: '{entity}'. "
                "Use alphanumeric characters and underscores only."
            )

    def _validate_records_iterator(self, records: Iterator[bytes]) -> None:
        """Validate that records is an Iterator[bytes].

        Args:
            records: Should be an Iterator yielding bytes.

        Raises:
            TypeError: If records is not an iterator.
        """
        if records is None:
            raise TypeError("records cannot be None, expected Iterator[bytes]")
        if not hasattr(records, "__iter__") or not hasattr(records, "__next__"):
            raise TypeError(
                f"records must be an Iterator[bytes], got {type(records).__name__}"
            )

    def _build_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]:
        """Build metadata dict for lineage tracking."""
        return {
            "run_id": str(run_id),
            "run_type": run_type.value,
            "ingestion_ts": effective_ts.isoformat(),
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
        }

    def _write_atomic_bronze(
        self, data: bytes, path: Path, metadata: dict[str, str], meta_path: Path
    ) -> None:
        """Write data and metadata atomically using temp files + rename."""
        with AtomicWriteGroup() as group:
            group.add(path, data)
            group.add(meta_path, json.dumps(metadata).encode("utf-8"))
            group.commit()

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> Path:
        """Write raw records to Bronze layer (JSONL + zstd).

        Args:
            records: Iterator of JSON-encoded record bytes.
            provider: Provider name (e.g., 'chembl').
            entity: Entity type (e.g., 'activity').
            date: Date for path partitioning.
            batch_id: Unique identifier for this batch.
            run_id: Pipeline run identifier.
            run_type: Type of run (incremental, backfill, etc.).
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014).

        Returns:
            Relative path to the written file.

        """
        self._validate_bronze_names(provider, entity)
        self._validate_records_iterator(records)

        date_str = date.strftime("%Y-%m-%d")
        relative_path = (
            f"bronze/v1/{provider}/{entity}/{date_str}/batch_{batch_id}.jsonl.zst"
        )
        metadata = self._build_bronze_metadata(
            run_id, run_type, ingestion_ts, provider, entity, batch_id
        )

        loop = asyncio.get_running_loop()

        if self.save_json:
            record_list = list(records)
            records_iter = iter(record_list)
        else:
            record_list = []
            records_iter = records

        compressed_data = await loop.run_in_executor(
            None, self._compress_records, records_iter
        )
        if not compressed_data:
            raise ValueError("No records to write")

        full_path = self.base_path / relative_path
        meta_path = full_path.with_suffix(".zst.meta.json")

        await loop.run_in_executor(
            None,
            lambda: self._write_atomic_bronze(
                compressed_data, full_path, metadata, meta_path
            ),
        )

        self.logger.info(
            "bronze_write_complete",
            path=relative_path,
            provider=provider,
            entity=entity,
            batch_id=str(batch_id),
            run_id=str(run_id),
            run_type=run_type.value,
        )

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
        """Write uncompressed JSONL copy of records atomically."""
        from bioetl.infrastructure.storage._atomic import atomic_write_bytes

        json_relative_path = f"{provider}/{entity}/batch_{date_str}_{batch_id}.jsonl"

        # Combine all records into single JSONL content
        jsonl_content = b"".join(records)

        json_full_path = Path(self.json_path) / json_relative_path
        json_full_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: atomic_write_bytes(json_full_path, jsonl_content),
        )

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
                    # Pass bytearray directly to avoid memory copy
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
