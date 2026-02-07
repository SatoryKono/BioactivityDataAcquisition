"""Bronze layer writer (local storage with JSONL + zstd compression).

Implements RULES.md §2.1.1 - Bronze Layer specifications.

Requirements:
- REQ-DATA-001: JSONL + zstd format
- REQ-DATA-002: Path format bronze/{provider}/{entity}/{date}/
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
    COMPRESSION_THREADS = -1  # zstd: auto-detect available CPU cores

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
        flat_structure: bool = False,
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
            flat_structure: If True, write directly to base_path/{date}/ without
                          adding {provider}/{entity}/ prefix. Use when base_path
                          already includes provider/entity path segments.

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
        self._flat_structure = flat_structure

    def _resolve_bronze_path(
        self, provider: str, entity: str, date_str: str, filename: str
    ) -> str:
        """Resolve Bronze file path based on flat_structure setting.

        Args:
            provider: Data provider name (e.g., 'chembl').
            entity: Entity type (e.g., 'document').
            date_str: Date string in YYYY-MM-DD format.
            filename: File name (e.g., 'batch_2026-01-21_uuid.jsonl.zst').

        Returns:
            Relative path from base_path to the file.

        Path formats:
            flat_structure=False: {provider}/{entity}/{date}/{filename}
            flat_structure=True:  {date}/{filename}
        """
        if self._flat_structure:
            return f"{date_str}/{filename}"
        return f"{provider}/{entity}/{date_str}/{filename}"

    def _validate_bronze_names(self, provider: str, entity: str) -> None:
        """Validate provider and entity names (alphanumeric + underscores only)."""
        for name, label in [(provider, "provider"), (entity, "entity")]:
            if not name or not name.replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid {label} name: '{name}'. "
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
        """Validate that datetime is timezone-aware and in UTC."""
        if dt.tzinfo is None:
            raise ValueError(f"{param_name} must be timezone-aware (UTC).")
        if dt.tzinfo.utcoffset(dt) != timedelta(0):
            raise ValueError(f"{param_name} must be UTC (offset 0).")

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
            BaseOutputMetadata,
            BronzeMetadata,
            BronzeOutputExt,
            EnvironmentMetadata,
            FileOutputMetadata,
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

        # Build file metadata for output_ext
        file_metadata = FileOutputMetadata(
            path=output_path,
            size_bytes=compressed_size,
            record_count=record_count,
        )

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
            output=BaseOutputMetadata(
                record_count=record_count,
                total_bytes=compressed_size,
                write_started_at=started_at,
                write_completed_at=completed_at,
            ),
            output_ext=BronzeOutputExt(
                files=[file_metadata],
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
            # Path format depends on flat_structure:
            #   flat_structure=False: {provider}/{entity}/{date}/batch_...
            #   flat_structure=True:  {date}/batch_...
            filename = f"batch_{date_str}_{batch_id}.jsonl.zst"
            relative_path = self._resolve_bronze_path(
                provider, entity, date_str, filename
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

                # Write to entity directory (not date subdirectory) - unified with Silver
                # flat_structure=True: base_path already includes provider/entity
                # flat_structure=False: base_path/{provider}/{entity}/
                if self._flat_structure:
                    metadata_base_path = self.base_path
                else:
                    metadata_base_path = self.base_path / provider / entity
                await self._metadata_writer.write_bronze_metadata(
                    base_path=metadata_base_path,
                    metadata=bronze_metadata,
                    provider=provider,
                    entity=entity,
                )
                self.logger.debug(
                    "bronze_metadata_written",
                    metadata_path=str(
                        metadata_base_path / f"{provider}_{entity}_metadata.yaml"
                    ),
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
        """Write uncompressed JSONL copy of records atomically.

        JSON copy is written in the same directory as the compressed zst file
        for easier access and co-location of data artifacts.
        """
        # JSON copy is now stored alongside the zst file in the same directory
        json_filename = f"batch_{date_str}_{batch_id}.jsonl"
        json_relative_path = self._resolve_bronze_path(
            provider, entity, date_str, json_filename
        )

        # Combine all records into single JSONL content
        jsonl_content = b"".join(records)

        # Use base_path (same location as zst files) instead of separate json_path
        json_full_path = self.base_path / json_relative_path
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
                return reader.read()  # type: ignore[no-any-return]

        decompressed_data = await asyncio.get_running_loop().run_in_executor(
            None, _read_and_decompress
        )
        for line in decompressed_data.decode("utf-8").splitlines():
            if line.strip():
                yield orjson.loads(line)

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """List all batch files for a given provider/entity.

        Path resolution depends on flat_structure setting:
        - flat_structure=False: {base_path}/{provider}/{entity}/{date}/
        - flat_structure=True: {base_path}/{date}/ (provider/entity in base_path)

        When flat_structure=True and provider/entity are empty strings,
        searches directly from base_path (used by CachedBronzeDataSource).

        Results are sorted lexicographically for deterministic ordering (ADR-014).
        """
        # Handle flat_structure mode (provider/entity already in base_path)
        if self._flat_structure and not provider and not entity:
            # Search directly from base_path
            if date:
                search_path = self.base_path / date.strftime("%Y-%m-%d")
            else:
                search_path = self.base_path
        else:
            # Standard path format: {provider}/{entity}/{date}/
            prefix = f"{provider}/{entity}/"
            if date:
                prefix = f"{prefix}{date.strftime('%Y-%m-%d')}/"
            search_path = self.base_path / prefix

        if not search_path.exists():
            return []

        pattern = "batch_*.jsonl.zst" if date else "**/*.jsonl.zst"
        files = list(search_path.glob(pattern))
        # Sort for deterministic ordering (ADR-014)
        return sorted(str(p.relative_to(self.base_path)) for p in files)

    def _find_old_date_dirs(
        self,
        cutoff_str: str,
        provider: str | None = None,
        entity: str | None = None,
    ) -> list[Path]:
        """Find date directories older than cutoff.

        Iterates over {base_path}/{provider}/{entity}/{date}/ structure.
        Optionally filters by provider and entity.
        """
        if not self.base_path.exists():
            return []

        pattern = f"{provider or '*'}/{entity or '*'}"
        old_dirs: list[Path] = []

        # Use glob to filter provider/entity structure efficiently
        for entity_dir in self.base_path.glob(pattern):
            if not entity_dir.is_dir():
                continue

            for date_dir in entity_dir.iterdir():
                if self._is_old_date_dir(date_dir, cutoff_str):
                    old_dirs.append(date_dir)

        return old_dirs

    def _is_old_date_dir(self, path: Path, cutoff_str: str) -> bool:
        """Check if path is a date directory older than cutoff."""
        return path.is_dir() and len(path.name) == 10 and path.name < cutoff_str

    async def cleanup_old_files(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention)."""
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        files, bytes_total, dirs = 0, 0, 0

        for date_dir in self._find_old_date_dirs(cutoff_str, provider, entity):
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
