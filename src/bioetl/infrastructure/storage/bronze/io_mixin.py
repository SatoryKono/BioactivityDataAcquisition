"""I/O helpers for BronzeWriter."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import zstandard as zstd

from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)
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


class BronzeWriterIOMixin(BronzeWriterReadCleanupMixin):
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

        return await asyncio.to_thread(_compute)

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


__all__ = ["BronzeWriterIOMixin"]
