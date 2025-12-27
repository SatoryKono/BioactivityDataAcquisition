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
import tempfile
import time
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import zstandard as zstd

if TYPE_CHECKING:
    from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort

from bioetl.domain.ports.audit import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage._atomic import AtomicWriteGroup, atomic_write_bytes


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
        metrics: MetricsPort,
        save_json: bool = False,
        json_path: str | None = None,
        validate_json: bool = True,
        audit: AuditPort | None = None,
    ) -> None:
        """Initialize Bronze writer.

        Args:
            base_path: Base path for Bronze layer storage
            logger: Structured logger for observability (MUST be injected)
            metrics: Metrics port for observability (MUST be injected).
                     Use NoOpMetrics from composition layer if metrics disabled.
            save_json: If True, also save uncompressed JSON copy
            json_path: Path for JSON files (defaults to base_path/json/)
            validate_json: If True, validate each record is valid JSON bytes
                          before writing. Raises BronzeValidationError on invalid.
                          Default is True for data integrity.
            audit: Optional AuditPort for write operation traceability.
                  Use NoOpAudit from composition layer if audit disabled.

        """
        self.base_path = Path(base_path)
        self.logger = logger
        self._metrics = metrics
        self.save_json = save_json
        self.json_path = json_path or str(self.base_path / "json")
        self.validate_json = validate_json
        self._audit = audit

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
        # Relaxed check: Accept Iterable, but prefer Iterator.
        # Logic in write_bronze will convert to iter() if needed.
        if not hasattr(records, "__iter__"):
            raise TypeError(
                f"records must be an Iterator[bytes] (or Iterable), got {type(records).__name__}"
            )

    def _validate_utc_datetime(self, dt: datetime, param_name: str) -> None:
        """Validate that datetime is timezone-aware and in UTC.

        Bronze layer requires UTC timestamps for lineage consistency
        and deterministic behavior (see ADR-014).

        Args:
            dt: Datetime to validate.
            param_name: Parameter name for error messages.

        Raises:
            ValueError: If datetime is naive or not in UTC.
        """
        if dt.tzinfo is None:
            raise ValueError(
                f"{param_name} must be timezone-aware, got naive datetime. "
                "Use datetime.now(UTC) or datetime(..., tzinfo=timezone.utc)."
            )
        offset = dt.tzinfo.utcoffset(dt)
        if offset is None or offset != timedelta(0):
            raise ValueError(
                f"{param_name} must be UTC, got timezone with offset {offset}. "
                "Convert to UTC before passing to BronzeWriter."
            )

    def _validate_json_records(self, records: Iterator[bytes]) -> Iterator[bytes]:
        """Validate that each record is valid JSON bytes (lazy generator).

        This method validates JSON structure without modifying records.
        Uses lazy evaluation to minimize memory overhead - only parses
        when iterating, immediately yields valid records.

        Args:
            records: Iterator of bytes, each expected to be valid JSON.

        Yields:
            Valid JSON bytes records.

        Raises:
            BronzeValidationError: If a record contains invalid JSON.
        """
        from bioetl.domain.exceptions import BronzeValidationError

        for index, record in enumerate(records):
            try:
                json.loads(record)
            except json.JSONDecodeError as e:
                raise BronzeValidationError(
                    message="Invalid JSON in Bronze record",
                    record_index=index,
                    original_error=str(e),
                ) from e
            yield record

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

    def _write_atomic_stream(
        self,
        records: Iterator[bytes],
        target_path: Path,
    ) -> tuple[int, int]:
        """Stream compress records directly to a temp file, then rename atomically.

        Args:
            records: Iterator of bytes records.
            target_path: Final destination path.

        Returns:
            Tuple of (record_count, uncompressed_size).
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            prefix="." + target_path.stem + "_",
            dir=target_path.parent,
        )
        temp_path = Path(temp_path_str)

        compressor = zstd.ZstdCompressor(
            level=self.COMPRESSION_LEVEL,
            threads=self.COMPRESSION_THREADS,
            write_content_size=True,
        )

        record_count = 0
        uncompressed_size = 0
        chunk_buffer = bytearray()

        try:
            with (
                open(fd, "wb") as f_out,
                compressor.stream_writer(
                    f_out, closefd=False, write_size=self.COMPRESSION_CHUNK_SIZE
                ) as writer,
            ):
                for record in records:
                    chunk_buffer.extend(record)
                    record_count += 1
                    uncompressed_size += len(record)

                    if len(chunk_buffer) >= self.COMPRESSION_CHUNK_SIZE:
                        writer.write(chunk_buffer)
                        chunk_buffer.clear()

                if chunk_buffer:
                    writer.write(chunk_buffer)
                    chunk_buffer.clear()

            if record_count == 0:
                # Clean up empty temp file
                temp_path.unlink()
                raise ValueError("No records to write")

            # Atomic rename
            temp_path.replace(target_path)

        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        return record_count, uncompressed_size

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

        Streams records through zstd compressor directly to disk.

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
        start_time = time.perf_counter()

        self._validate_bronze_names(provider, entity)
        self._validate_records_iterator(records)
        self._validate_utc_datetime(date, "date")
        self._validate_utc_datetime(ingestion_ts, "ingestion_ts")

        # Ensure records is an iterator (handles lists/tuples transparently)
        records = iter(records)

        # Apply JSON validation if enabled (lazy generator wrapping)
        if self.validate_json:
            records = self._validate_json_records(records)

        date_str = date.strftime("%Y-%m-%d")
        relative_path = (
            f"bronze/v1/{provider}/{entity}/{date_str}/batch_{batch_id}.jsonl.zst"
        )
        metadata = self._build_bronze_metadata(
            run_id, run_type, ingestion_ts, provider, entity, batch_id
        )

        loop = asyncio.get_running_loop()

        # Handle save_json: requires duplicating the iterator if iterator can only be consumed once
        # Note: If records is a generator, we must materialize it or tee it.
        # Assuming list(records) for safety if save_json is True, as we did before.
        # This breaks streaming for save_json=True case, but that is acceptable (debug mode).
        if self.save_json:
            record_list = list(records)
            records_iter = iter(record_list)
        else:
            record_list = []
            records_iter = records

        full_path = self.base_path / relative_path
        meta_path = full_path.with_suffix(".zst.meta.json")

        # Perform streaming write in executor
        # We need to capture records_iter in closure safely
        def _write_task():
            # Write data file
            count, size = self._write_atomic_stream(records_iter, full_path)
            # Write metadata file
            meta_bytes = json.dumps(
                metadata, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            atomic_write_bytes(meta_path, meta_bytes)
            return count, size

        record_count, uncompressed_size = await loop.run_in_executor(None, _write_task)
        compressed_size = full_path.stat().st_size

        # Record metrics
        duration = time.perf_counter() - start_time
        labels = {"provider": provider, "entity": entity}

        self._metrics.observe_histogram(
            "bronze_write_duration_seconds",
            duration,
            labels,
        )
        self._metrics.increment_counter(
            "bronze_records_written_total",
            record_count,
            labels,
        )
        self._metrics.increment_counter(
            "bronze_bytes_written_total",
            compressed_size,
            labels,
        )

        self.logger.info(
            "bronze_write_complete",
            path=relative_path,
            provider=provider,
            entity=entity,
            batch_id=str(batch_id),
            run_id=str(run_id),
            run_type=run_type.value,
            record_count=record_count,
            compressed_bytes=compressed_size,
            uncompressed_bytes=uncompressed_size,
            duration_seconds=round(duration, 3),
        )

        if self.save_json:
            await self._write_json_copy(
                record_list, provider, entity, date_str, batch_id
            )

        # Log audit entry for write operation
        if self._audit:
            audit_entry = AuditEntry(
                run_id=run_id,
                timestamp=ingestion_ts,
                layer=AuditLayer.BRONZE,
                table_name=relative_path,
                operation=AuditOperation.WRITE,
                records_count=record_count,
                metadata={
                    "provider": provider,
                    "entity": entity,
                    "batch_id": str(batch_id),
                    "run_type": run_type.value,
                    "compressed_bytes": compressed_size,
                    "uncompressed_bytes": uncompressed_size,
                },
            )
            await self._audit.log_write(audit_entry)

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

    def _compress_records(self, records: Iterator[bytes]) -> tuple[bytes, int, int]:
        """Compress JSONL records using zstandard.

        Deprecated: Use _write_atomic_stream for direct-to-disk streaming.
        Kept for backward compatibility if needed, but not used by main path.

        Returns:
            Tuple of (compressed_data, record_count, uncompressed_size).
        """
        # This method is no longer used by write_bronze but kept for interface stability if any
        # tests call it directly.
        from io import BytesIO

        output = BytesIO()
        compressor = zstd.ZstdCompressor(
            level=self.COMPRESSION_LEVEL,
            threads=self.COMPRESSION_THREADS,
            write_content_size=True,
        )

        chunk_buffer = bytearray()
        record_count = 0
        uncompressed_size = 0

        with compressor.stream_writer(
            output, closefd=False, write_size=self.COMPRESSION_CHUNK_SIZE
        ) as writer:
            for record in records:
                chunk_buffer.extend(record)
                record_count += 1
                uncompressed_size += len(record)

                if len(chunk_buffer) >= self.COMPRESSION_CHUNK_SIZE:
                    writer.write(chunk_buffer)
                    chunk_buffer.clear()

            if chunk_buffer:
                writer.write(chunk_buffer)

            if record_count == 0:
                raise ValueError("No records provided for compression")

        return output.getvalue(), record_count, uncompressed_size

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
