"""I/O helpers for BronzeWriter."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import orjson
import zstandard as zstd

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_bytes

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.domain.types import BatchID

BRONZE_WRITE_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    zstd.ZstdError,
)


class BronzeWriterIOMixin:
    """Mixin with write/read/list/cleanup filesystem operations."""

    base_path: Path
    logger: LoggerPort
    _logger: LoggerPort
    _metrics: MetricsPort
    COMPRESSION_LEVEL: int
    COMPRESSION_THREADS: int
    COMPRESSION_CHUNK_SIZE: int
    _flat_structure: bool
    _resolve_bronze_path: Callable[[str, str, str, str], str]

    def _write_atomic_stream(
        self,
        records: Iterator[bytes],
        target_path: Path,
    ) -> tuple[int, int]:
        """Stream-compress records to a temp file, then rename atomically."""
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
                temp_path.unlink()
                raise ValueError("No records to write")
            temp_path.replace(target_path)
        except BRONZE_WRITE_ERRORS:
            if temp_path.exists():
                temp_path.unlink()
            raise
        return record_count, uncompressed_size

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate BLAKE2b checksum of a file asynchronously."""
        import hashlib

        def _compute() -> str:
            h = hashlib.blake2b()
            with open(file_path, "rb") as f:
                for block in iter(lambda: f.read(65536), b""):
                    h.update(block)
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
        """Write uncompressed JSONL copy atomically."""
        json_filename = f"batch_{date_str}_{batch_id}.jsonl"
        json_relative_path = self._resolve_bronze_path(
            provider, entity, date_str, json_filename
        )

        jsonl_content = b"".join(records)

        json_full_path = self.base_path / json_relative_path
        json_full_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: atomic_write_bytes(json_full_path, jsonl_content),
        )

    async def read_bronze(
        self, path: str
    ) -> AsyncIterator[JsonDict]:  # Any: record/metadata values are heterogeneous
        """Read and decompress Bronze file (for testing/debugging)."""
        full_path = self.base_path / path

        def _read_and_decompress() -> bytes:
            with open(full_path, "rb") as f:
                compressed_data = f.read()
            decompressor = zstd.ZstdDecompressor()
            with decompressor.stream_reader(compressed_data) as reader:
                data: bytes = reader.read()
                return data

        decompressed_data = await asyncio.get_running_loop().run_in_executor(
            None, _read_and_decompress
        )
        for line in decompressed_data.decode("utf-8").splitlines():
            if line.strip():
                yield orjson.loads(line)

    def _list_batches_sync(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """Sync body for list_batches with blocking Path I/O."""
        if self._flat_structure and not provider and not entity:
            search_path = (
                self.base_path / date.strftime("%Y-%m-%d") if date else self.base_path
            )
        else:
            prefix = f"{provider}/{entity}/"
            if date:
                prefix = f"{prefix}{date.strftime('%Y-%m-%d')}/"
            search_path = self.base_path / prefix

        if not search_path.exists():
            return []

        pattern = "batch_*.jsonl.zst" if date else "**/*.jsonl.zst"
        files = list(search_path.glob(pattern))
        return sorted(str(p.relative_to(self.base_path)) for p in files)

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """List all batch files for a given provider/entity."""
        result = await asyncio.to_thread(
            self._list_batches_sync, provider, entity, date
        )
        self._logger.debug(
            "bronze_list_batches",
            provider=provider,
            entity=entity,
            batch_count=len(result),
        )
        return result

    def _find_old_date_dirs(
        self,
        cutoff_str: str,
        provider: str | None = None,
        entity: str | None = None,
    ) -> list[Path]:
        """Find date directories older than cutoff."""
        if not self.base_path.exists():
            return []

        pattern = f"{provider or '*'}/{entity or '*'}"
        old_dirs: list[Path] = []

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

    def _cleanup_old_files_sync(
        self,
        cutoff_str: str,
        dry_run: bool,
        provider: str | None,
        entity: str | None,
    ) -> tuple[int, int, int]:
        """Sync body for cleanup_old_files with blocking Path I/O."""
        files, bytes_total, dirs = 0, 0, 0

        for date_dir in self._find_old_date_dirs(cutoff_str, provider, entity):
            removed_files, removed_bytes = self._remove_old_dir_files(
                date_dir=date_dir,
                dry_run=dry_run,
            )
            files += removed_files
            bytes_total += removed_bytes
            if dry_run or not any(date_dir.iterdir()):
                dirs += 1
                if not dry_run:
                    date_dir.rmdir()

        return files, bytes_total, dirs

    def _remove_old_dir_files(
        self,
        *,
        date_dir: Path,
        dry_run: bool,
    ) -> tuple[int, int]:
        """Remove all files from one old Bronze date directory."""
        files_removed = 0
        bytes_removed = 0
        for file_path in date_dir.glob("*"):
            if not file_path.is_file():
                continue
            bytes_removed += file_path.stat().st_size
            files_removed += 1
            if not dry_run:
                file_path.unlink()
        return files_removed, bytes_removed

    async def cleanup_old_files(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention)."""
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        files, bytes_total, dirs = await asyncio.to_thread(
            self._cleanup_old_files_sync, cutoff_str, dry_run, provider, entity
        )

        self._logger.info(
            "bronze_cleanup_complete",
            cutoff=cutoff_str,
            dry_run=dry_run,
            files_removed=files,
            bytes_freed=bytes_total,
            dirs_removed=dirs,
        )
        if not dry_run and files > 0:
            cleanup_labels = {"operation": "cleanup"}
            self._metrics.increment_counter(
                "bioetl_bronze_files_removed_total",
                files,
                cleanup_labels,
            )
            self._metrics.increment_counter(
                "bioetl_bronze_bytes_freed_total",
                bytes_total,
                cleanup_labels,
            )
        return {
            "files_removed": files,
            "bytes_freed": bytes_total,
            "directories_removed": dirs,
        }

    def preview_cleanup(
        self,
        provider: str | None = None,
        entity: str | None = None,
    ) -> JsonDict:  # Any: preview payload has heterogeneous values
        """Preview Bronze cleanup scope without deleting files."""
        preview_root = self._resolve_bronze_preview_root(provider, entity)
        exists = preview_root.exists()
        file_count = (
            sum(1 for file_path in preview_root.rglob("*") if file_path.is_file())
            if exists
            else 0
        )

        return {
            "path": str(preview_root),
            "file_count": file_count,
            "exists": exists,
        }

    def _resolve_bronze_preview_root(
        self,
        provider: str | None,
        entity: str | None,
    ) -> Path:
        """Resolve Bronze preview root for optional provider/entity filters."""
        if self._flat_structure:
            return self.base_path
        if provider and entity:
            return self.base_path / provider / entity
        if provider:
            return self.base_path / provider
        return self.base_path


__all__ = ["BronzeWriterIOMixin"]
