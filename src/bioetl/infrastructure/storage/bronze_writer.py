"""Bronze layer writer.

Handles writing raw data to Bronze layer (JSON Lines, compressed).

Refactored to match project standards:
- Use fixed timestamps (ingestion_ts) from context (Phase 5).
- Validate provider/entity names.
- Ensure metadata consistency.
- ATOMIC writes (temp file + rename).
- Async I/O (compression/write in executor).
- Metadata sidecar support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Any

import zstandard as zstd

from bioetl.domain.types import BatchID, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class BronzeWriter:
    """Writes raw data to the Bronze layer (compressed JSONL).

    Features:
    - Writes immutable files with run metadata.
    - Uses Zstandard compression for efficiency.
    - Path structure: bronze/v1/{provider}/{entity}/{date}/{batch_id}.jsonl.zst
    - Atomic writes (temp -> rename).
    - Async execution to prevent blocking event loop.
    - Writes accompanying .meta.json file.
    """

    def __init__(self, base_path: Path, logger: LoggerPort | None = None) -> None:
        self.base_path = base_path
        self.logger = logger
        self._format_version = "v1"

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
        """Write raw records to Bronze storage.

        Args:
            records: Iterator of raw bytes (JSON lines).
            provider: Data provider name.
            entity: Entity type name.
            date: Date for partitioning (usually execution date).
            batch_id: Unique batch identifier.
            run_id: Pipeline run identifier.
            run_type: Type of run (initial, incremental, etc).
            ingestion_ts: Timestamp of ingestion (from PipelineContext).

        Returns:
            Path to the written file.

        Raises:
            ValueError: If provider/entity names are invalid.
            IOError: If write fails.

        """
        # 1. Validate inputs (M3)
        if not provider or not provider.replace("_", "").isalnum():
            raise ValueError(f"Invalid provider name: '{provider}'")
        if not entity or not entity.replace("_", "").isalnum():
            raise ValueError(f"Invalid entity name: '{entity}'")

        # Ensure records is iterable (though type hint says Iterator)
        if not isinstance(records, (Iterator, list)):
             raise TypeError(f"records must be an Iterator or list, got {type(records)}")

        # 2. Construct path
        # bronze/v1/{provider}/{entity}/{date}/
        date_str = date.strftime("%Y-%m-%d")
        dir_path = (
            self.base_path
            / self._format_version
            / provider
            / entity
            / date_str
        )
        # Directory creation is fast/cached usually, but strictly should be async?
        # pathlib mkdir is blocking. Usually acceptable for setup, but let's be strict.
        # But commonly we just do it.
        dir_path.mkdir(parents=True, exist_ok=True)

        filename = f"{batch_id}.jsonl.zst"
        file_path = dir_path / filename
        meta_path = dir_path / f"{batch_id}.meta.json"

        # 3. Offload blocking I/O to executor
        loop = asyncio.get_running_loop()
        try:
            # We must consume the iterator in the executor if it's blocking?
            # Or assume iterator is in-memory/fast?
            # If records is a generator doing network I/O, this is tricky.
            # But usually records are bytes in memory or from a fast source.
            # Passing generator to executor might work if it doesn't touch async stuff.

            # The safest way is to wrap the whole file operation.
            await loop.run_in_executor(
                None,
                self._write_file_sync,
                file_path,
                records,
                meta_path,
                batch_id,
                run_id,
                run_type,
                ingestion_ts,
                provider,
                entity,
            )
        except Exception as e:
            if self.logger:
                self.logger.error(
                    "Failed to write bronze file",
                    file=str(file_path),
                    error=str(e),
                )
            raise IOError(f"Failed to write bronze file {file_path}: {e}") from e

        if self.logger:
            self.logger.info(
                "Written bronze file",
                file=str(file_path),
                size=file_path.stat().st_size,
                ingestion_ts=ingestion_ts.isoformat(),
            )

        return file_path

    def _write_file_sync(
        self,
        file_path: Path,
        records: Iterator[bytes],
        meta_path: Path,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        provider: str,
        entity: str,
    ) -> None:
        """Synchronous implementation of file writing (atomic)."""
        dir_path = file_path.parent
        tmp_path = None

        try:
            # Create temp file in the same directory to ensure atomic rename works
            with tempfile.NamedTemporaryFile(
                dir=dir_path,
                prefix=f".tmp_{batch_id}_",
                suffix=".zst",
                delete=False
            ) as tmp_file:
                tmp_path = Path(tmp_file.name)
                cctx = zstd.ZstdCompressor()
                with cctx.stream_writer(tmp_file) as compressor:
                    for record_bytes in records:
                        compressor.write(record_bytes)
                        compressor.write(b"\n")

            # Atomic Rename
            tmp_path.replace(file_path)

            # Write Metadata Sidecar
            metadata = self._build_bronze_metadata(
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
                provider=provider,
                entity=entity,
            )
            with meta_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

        except Exception:
            # Cleanup temp file if exists and we failed
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            raise

    def _build_bronze_metadata(
        self,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        provider: str,
        entity: str,
    ) -> dict[str, Any]:
        """Build metadata for the bronze file."""
        return {
            "batch_id": str(batch_id),
            "run_id": str(run_id),
            "run_type": run_type.value,
            "ingestion_ts": ingestion_ts.isoformat(),
            "provider": provider,
            "entity": entity,
            "format": "jsonl.zst",
            "version": self._format_version,
        }

    def _compress_records(self, records: Iterator[bytes]) -> bytes:
        """Compress records using Zstandard (helper for tests)."""
        cctx = zstd.ZstdCompressor()
        compressed_chunks = []
        # Use a simple buffer-like object or BytesIO
        import io
        buffer = io.BytesIO()
        with cctx.stream_writer(buffer) as compressor:
             for record_bytes in records:
                compressor.write(record_bytes)
                compressor.write(b"\n")
        return buffer.getvalue()

    async def read_bronze(self, file_path: Path) -> Iterator[dict[str, Any]]:
        """Read records from a Bronze file.

        Args:
            file_path: Path to the .jsonl.zst file.

        Yields:
            Parsed JSON records.

        """
        if not file_path.exists():
            raise FileNotFoundError(f"Bronze file not found: {file_path}")

        # Offload decompression? For large files, streaming in main thread
        # might block if processing is heavy, but usually read is IO bound.
        # But unzipping is CPU bound.
        # Ideally we stream.
        # Existing implementation was sync in async?
        # Let's keep it simple or use run_in_executor for full read if small.
        # For iterator, it's complex to offload to executor without thread coordination.
        # Assuming current usage is acceptable or tests expect it.

        dctx = zstd.ZstdDecompressor()
        with file_path.open("rb") as f:
            with dctx.stream_reader(f) as reader:
                import io
                text_stream = io.TextIOWrapper(reader, encoding="utf-8")
                for line in text_stream:
                    if line.strip():
                        yield json.loads(line)
