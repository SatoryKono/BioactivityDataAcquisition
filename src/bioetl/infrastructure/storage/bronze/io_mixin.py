# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""I/O helpers for BronzeWriter."""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import zstandard as zstd

from bioetl.infrastructure.storage.bronze.facade_contracts import BRONZE_WRITE_ERRORS
from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)
from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_bytes

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.domain.types import BatchID


class BronzeWriterIOMixin(BronzeWriterReadCleanupMixin):
    """Mixin with write/read/list/cleanup filesystem operations."""

    base_path: Path = cast(Any, None)  # Any: host attr default (PD6)
    logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD6)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD6)
    _metrics: MetricsPort = cast(Any, None)  # Any: host attr default (PD6)
    COMPRESSION_LEVEL: int = cast(Any, None)  # Any: host attr default (PD6)
    COMPRESSION_THREADS: int = cast(Any, None)  # Any: host attr default (PD6)
    COMPRESSION_CHUNK_SIZE: int = cast(Any, None)  # Any: host attr default (PD6)
    _flat_structure: bool = cast(Any, None)  # Any: host attr default (PD6)
    _resolve_bronze_path: Callable[[str, str, str, str], str] = cast(
        Any, None
    )  # Any: host attr default (PD6)

    def _effective_compression_threads(self) -> int:
        """Return a memory-safe zstd thread count.

        Negative values mean "all cores" in python-zstandard. Multi-thread
        compression allocates a large CCTX per worker and has OOM'd Windows
        publication bronze writes (`Allocation error : not enough memory`).
        """
        threads = int(self.COMPRESSION_THREADS)
        if threads < 0:
            return 0
        return threads

    def _build_stream_compressor(self) -> zstd.ZstdCompressor:
        """Build a streaming compressor that does not pledge content size.

        `write_content_size=True` is for known-length frames. On
        ``stream_writer`` the size is unknown, and pledging it can force
        extra buffering on top of the already-resident batch payload.
        """
        return zstd.ZstdCompressor(
            level=self.COMPRESSION_LEVEL,
            threads=self._effective_compression_threads(),
            write_content_size=False,
        )

    def _finalize_atomic_stream_write(
        self,
        *,
        target_path: Path,
        temp_path: Path,
        record_count: int,
        uncompressed_size: int,
    ) -> tuple[int, int]:
        """Validate non-empty stream write and atomically publish temp payload."""
        if record_count == 0:
            raise ValueError("No records to write")
        if target_path.exists():
            if not self._compressed_payload_matches(target_path, temp_path):
                raise FileExistsError(
                    f"Bronze target already exists with different payload: {target_path}"
                )
        else:
            temp_path.replace(target_path)
        return record_count, uncompressed_size

    def _write_atomic_stream(
        self,
        records: Iterator[bytes],
        target_path: Path,
    ) -> tuple[int, int]:
        """Stream-compress records to a temp file, then rename atomically."""
        import os

        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            prefix="." + target_path.stem + "_",
            dir=target_path.parent,
        )
        temp_path = Path(temp_path_str)
        # Track raw-fd ownership until open() takes over, so setup failures
        # never leak the mkstemp descriptor.
        fd_owned = True
        record_count = 0
        uncompressed_size = 0
        chunk_buffer = bytearray()
        try:
            try:
                compressor = self._build_stream_compressor()
            except BRONZE_WRITE_ERRORS:
                os.close(fd)
                fd_owned = False
                raise
            with (
                open(fd, "wb") as f_out,
                compressor.stream_writer(
                    f_out, closefd=False, write_size=self.COMPRESSION_CHUNK_SIZE
                ) as writer,
            ):
                fd_owned = False  # open() now owns the descriptor
                for record in records:
                    chunk_buffer.extend(record)
                    record_count += 1
                    uncompressed_size += len(record)

                    if len(chunk_buffer) >= self.COMPRESSION_CHUNK_SIZE:
                        writer.write(bytes(chunk_buffer))
                        chunk_buffer.clear()

                if chunk_buffer:
                    writer.write(bytes(chunk_buffer))
                    chunk_buffer.clear()
            return self._finalize_atomic_stream_write(
                target_path=target_path,
                temp_path=temp_path,
                record_count=record_count,
                uncompressed_size=uncompressed_size,
            )
        finally:
            if fd_owned:
                with contextlib.suppress(OSError):
                    os.close(fd)
            # Drop leftover temp on failure / idempotent-match success.
            # Successful replace renames the temp away so this is a no-op.
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

    def _compressed_payload_matches(self, left: Path, right: Path) -> bool:
        """Compare compressed Bronze payloads by full decompressed streams.

        Chunks are concatenated before comparison so differing stream-reader
        boundaries cannot produce false mismatches.
        """
        left_dctx = zstd.ZstdDecompressor()
        right_dctx = zstd.ZstdDecompressor()
        with (
            left.open("rb") as left_file,
            right.open("rb") as right_file,
            left_dctx.stream_reader(left_file) as left_reader,
            right_dctx.stream_reader(right_file) as right_reader,
        ):
            left_payload = left_reader.read()
            right_payload = right_reader.read()
            return left_payload == right_payload

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

        def _write() -> None:
            json_filename = f"batch_{date_str}_{batch_id}.jsonl"
            json_relative_path = self._resolve_bronze_path(
                provider, entity, date_str, json_filename
            )

            jsonl_content = b"".join(records)

            json_full_path = self.base_path / json_relative_path
            json_full_path.parent.mkdir(parents=True, exist_ok=True)
            if json_full_path.exists():
                if json_full_path.read_bytes() == jsonl_content:
                    return
                raise FileExistsError(
                    "Bronze JSON copy already exists with different payload: "
                    f"{json_full_path}"
                )

            atomic_write_bytes(json_full_path, jsonl_content)

        await asyncio.to_thread(_write)


__all__ = ["BronzeWriterIOMixin"]
