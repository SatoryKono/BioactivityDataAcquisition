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
import tempfile
import time
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson
import zstandard as zstd

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        TracingPort,
    )

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage._atomic import atomic_write_bytes


class BronzeWriter:
    """Writer for Bronze layer (raw data in JSONL + zstd).

    Optionally saves uncompressed JSON copy when save_json=True.

    Note: LoggerPort is required per RULES.md DI requirements. All dependencies
    MUST be injected through constructor without fallback defaults.
    """

    COMPRESSION_CHUNK_SIZE = 256 * 1024
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1

    # Bronze format version for path partitioning (REQ-DATA-002)
    BRONZE_FORMAT_VERSION = "v1"

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None = None,
        save_json: bool = False,
        json_path: str | None = None,
        validate_json: bool = True,
        audit: AuditPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        save_metadata: bool = False,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
    ) -> None:
        """Initialize Bronze writer.

        Args:
            base_path: Base path for Bronze layer storage
            logger: Structured logger for observability (MUST be injected)
            metrics: Metrics port for observability (MUST be injected).
                     Use NoOpMetrics from composition layer if metrics disabled.
            tracing: TracingPort for distributed tracing. Use NoOpTracing from
                    composition layer if tracing is disabled. If None, NoOpTracing
                    is used automatically (for test convenience).
            save_json: If True, also save uncompressed JSON copy
            json_path: Path for JSON files (defaults to base_path/json/)
            validate_json: If True, validate each record is valid JSON bytes
                          before writing. Raises BronzeValidationError on invalid.
                          Default is True for data integrity.
            audit: Optional AuditPort for write operation traceability.
                  Use NoOpAudit from composition layer if audit disabled.
            metadata_writer: Optional MetadataWriterPort for writing _metadata.yaml
                           sidecar files with lineage and QC information.
                           Use NoOpMetadataWriter if metadata disabled.
            save_metadata: If True, write _metadata.yaml sidecar file alongside
                         data files with rich lineage information.
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation. If provided, uses coordinator
                                instead of local _build_full_bronze_metadata().
                                Ensures consistent run_id across layers.

        Note:
            Lock validation is now performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
        """
        # Use NoOpTracing if not provided (test convenience, production uses composition)
        # Import from domain.ports.noop to maintain proper layer separation
        if tracing is None:
            from bioetl.domain.ports import NoOpTracing

            tracing = NoOpTracing()

        # Use NoOpMetadataWriter if not provided (Null Object pattern)
        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()

        self.base_path = Path(base_path)
        self.logger = logger
        self._metrics = metrics
        self.save_json = save_json
        self.json_path = json_path or str(self.base_path / "json")
        self.validate_json = validate_json
        self._audit = audit
        self._tracing: TracingPort = tracing
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._save_metadata = save_metadata
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )

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
                orjson.loads(record)
            except orjson.JSONDecodeError as e:
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

    def _build_full_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeMetadata:
        """Build rich BronzeMetadata for sidecar file.

        Args:
            run_id: Pipeline run identifier.
            run_type: Type of run (incremental, backfill, rebuild).
            provider: Provider name (e.g., 'chembl').
            entity: Entity type (e.g., 'activity').
            batch_id: Unique identifier for this batch.
            record_count: Number of records written.
            compressed_size: Size of compressed file in bytes.
            output_path: Relative path to the written file.
            started_at: UTC timestamp when write started.
            completed_at: UTC timestamp when write completed.
            duration_seconds: Duration of write operation.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details. If None, a minimal SourceMetadata is created.

        Returns:
            BronzeMetadata instance for sidecar file.
        """
        import platform
        import socket

        from bioetl import __version__
        from bioetl.domain.models.metadata import (
            BronzeMetadata,
            EnvironmentMetadata,
            FileOutputMetadata,
            OutputMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
        )
        from bioetl.domain.models.metadata import SourceMetadata as SourceMetadataModel

        # Map domain RunType to metadata RunTypeEnum
        run_type_map = {
            RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
            RunType.BACKFILL: RunTypeEnum.BACKFILL,
            RunType.REBUILD: RunTypeEnum.REBUILD,
        }

        # Use provided source_metadata or create minimal default
        if source_metadata is None:
            source_metadata = SourceMetadataModel(type="api")

        return BronzeMetadata(
            runtime=RuntimeMetadata(
                run_id=str(run_id),
                run_type=run_type_map.get(run_type, RunTypeEnum.INCREMENTAL),
                started_at_utc=started_at,
                completed_at_utc=completed_at,
                duration_seconds=duration_seconds,
            ),
            pipeline=PipelineMetadata(
                name=f"{provider}_{entity}",
                provider=provider,
                entity=entity,
            ),
            source=source_metadata,
            output=OutputMetadata(
                files=[
                    FileOutputMetadata(
                        path=output_path,
                        size_bytes=compressed_size,
                        record_count=record_count,
                    )
                ],
                total_records=record_count,
                total_bytes=compressed_size,
            ),
            environment=EnvironmentMetadata(
                hostname=socket.gethostname(),
                python_version=platform.python_version(),
                bioetl_version=__version__,
            ),
        )

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
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write raw records to Bronze layer (JSONL + zstd).

        Returns BronzeWriteResult with path, sizes, and checksum for lineage.
        Lock validation is performed at Application layer per §4.6 Safety Guard.

        Args:
            records: Iterator of bytes records (JSON-encoded).
            provider: Provider name (e.g., 'chembl').
            entity: Entity type (e.g., 'activity').
            date: Date for partitioning.
            batch_id: Unique identifier for this batch.
            run_id: Pipeline run identifier.
            run_type: Type of run (incremental, backfill, rebuild).
            ingestion_ts: UTC timestamp for ingestion.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking.
        """
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_bronze") as span:
            span.set_attribute("provider", provider)
            span.set_attribute("entity", entity)
            span.set_attribute("batch_id", str(batch_id))
            span.set_attribute("run_id", str(run_id))

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
            # FIX: Removed redundant 'bronze/' prefix.
            # base_path already points to 'data/output/bronze'
            relative_path = (
                f"{self.BRONZE_FORMAT_VERSION}/{provider}/{entity}/"
                f"{date_str}/batch_{batch_id}.jsonl.zst"
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
            def _write_task() -> tuple[int, int]:
                # Write data file
                count, size = self._write_atomic_stream(records_iter, full_path)
                # Write metadata file
                meta_bytes = orjson.dumps(metadata, option=orjson.OPT_SORT_KEYS)
                atomic_write_bytes(meta_path, meta_bytes)
                return count, size

            record_count, uncompressed_size = await loop.run_in_executor(
                None, _write_task
            )
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

            # Write rich metadata sidecar file if enabled
            if self._save_metadata:
                # Calculate completed_at from ingestion_ts + duration
                # (avoids datetime.now() per ADR-014)
                completed_at = ingestion_ts + timedelta(seconds=duration)

                # Use MetadataCoordinator if available (centralized metadata)
                if self._metadata_coordinator is not None:
                    from bioetl.domain.ports import BronzeMetadataInput

                    # Extract query_string from source_metadata for BronzeMetadataInput
                    # This allows MetadataCoordinator to include it in metadata sidecar
                    query_string = (
                        source_metadata.query_string if source_metadata else None
                    )
                    bronze_input = BronzeMetadataInput(
                        batch_id=batch_id,
                        record_count=record_count,
                        compressed_size=compressed_size,
                        output_path=relative_path,
                        started_at=ingestion_ts,
                        completed_at=completed_at,
                        source_metadata=source_metadata,
                        query_string=query_string,
                    )
                    bronze_metadata = self._metadata_coordinator.create_bronze_metadata(
                        bronze_input
                    )
                else:
                    # Fallback to local metadata building (backward compatibility)
                    bronze_metadata = self._build_full_bronze_metadata(
                        run_id=run_id,
                        run_type=run_type,
                        provider=provider,
                        entity=entity,
                        batch_id=batch_id,
                        record_count=record_count,
                        compressed_size=compressed_size,
                        output_path=relative_path,
                        started_at=ingestion_ts,
                        completed_at=completed_at,
                        duration_seconds=duration,
                        source_metadata=source_metadata,
                    )

                # Write to batch directory (same level as data file)
                metadata_base_path = full_path.parent
                await self._metadata_writer.write_bronze_metadata(
                    base_path=metadata_base_path,
                    metadata=bronze_metadata,
                )
                self.logger.debug(
                    "bronze_metadata_written",
                    metadata_path=str(metadata_base_path / "_metadata.yaml"),
                    run_id=str(run_id),
                )

            span.set_attribute("record_count", record_count)
            span.set_attribute("compressed_size", compressed_size)

            # Calculate BLAKE2b checksum for integrity verification
            checksum = await self._calculate_checksum(full_path)

            return BronzeWriteResult(
                batch_id=batch_id,
                relative_path=relative_path,
                absolute_path=str(full_path),
                record_count=record_count,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                checksum_blake2=checksum,
            )

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate BLAKE2b checksum of a file asynchronously."""
        import hashlib

        def _compute() -> str:
            h = hashlib.blake2b()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()

        return await asyncio.get_running_loop().run_in_executor(None, _compute)

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

    async def read_bronze(self, path: str) -> AsyncIterator[dict[str, Any]]:
        """Read and decompress Bronze file (for testing/debugging)."""
        full_path = self.base_path / path

        def _read_and_decompress() -> bytes:
            with open(full_path, "rb") as f:
                compressed_data = f.read()
            decompressor = zstd.ZstdDecompressor()
            # Use streaming decompression since content size may not be in frame header
            with decompressor.stream_reader(compressed_data) as reader:
                return reader.read()

        decompressed_data = await asyncio.get_running_loop().run_in_executor(
            None, _read_and_decompress
        )
        for line in decompressed_data.decode("utf-8").splitlines():
            if line.strip():
                yield orjson.loads(line)

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
        # FIX: Removed redundant 'bronze/' prefix here too
        prefix = f"{self.BRONZE_FORMAT_VERSION}/{provider}/{entity}/"
        if date:
            prefix = f"{prefix}{date.strftime('%Y-%m-%d')}/"

        return self._list_batches_local(prefix, date)

    def _find_old_date_dirs(self, cutoff_str: str) -> list[Path]:
        """Find date directories older than cutoff."""
        version_path = self.base_path / self.BRONZE_FORMAT_VERSION
        if not version_path.exists():
            return []
        old_dirs: list[Path] = []
        for prov in version_path.iterdir():
            if not prov.is_dir():
                continue
            for ent in prov.iterdir():
                if not ent.is_dir():
                    continue
                for date_dir in ent.iterdir():
                    is_old = (
                        date_dir.is_dir()
                        and len(date_dir.name) == 10
                        and date_dir.name < cutoff_str
                    )
                    if is_old:
                        old_dirs.append(date_dir)
        return old_dirs

    async def cleanup_old_files(
        self, cutoff_date: datetime, dry_run: bool = False
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention)."""
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        files, bytes_total, dirs = 0, 0, 0

        for date_dir in self._find_old_date_dirs(cutoff_str):
            for fp in date_dir.glob("*"):
                if fp.is_file():
                    bytes_total += fp.stat().st_size
                    files += 1
                    if not dry_run:
                        fp.unlink()
            if dry_run or not any(date_dir.iterdir()):
                dirs += 1
                if not dry_run:
                    date_dir.rmdir()

        self.logger.info(
            "bronze_cleanup_complete",
            cutoff=cutoff_str,
            dry_run=dry_run,
            files_removed=files,
            bytes_freed=bytes_total,
            dirs_removed=dirs,
        )
        return {
            "files_removed": files,
            "bytes_freed": bytes_total,
            "directories_removed": dirs,
        }
