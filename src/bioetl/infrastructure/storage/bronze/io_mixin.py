# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""I/O helpers for BronzeWriter."""

from __future__ import annotations

import asyncio
import contextlib
import errno
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import zstandard as zstd

from bioetl.infrastructure.storage.bronze.facade_contracts import BRONZE_WRITE_ERRORS
from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)

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
    ) -> None:
        """Validate non-empty stream write and atomically publish temp payload."""
        if record_count == 0:
            raise ValueError("No records to write")
        if _existing_payload_matches(
            target_path, temp_path, self._compressed_payload_matches
        ):
            return
        try:
            _publish_new_file_exclusive(temp_path, target_path)
        except FileExistsError:
            if _existing_payload_matches(
                target_path, temp_path, self._compressed_payload_matches
            ):
                return
            raise FileExistsError(
                f"Bronze target already exists with different payload: {target_path}"
            ) from None

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
            self._finalize_atomic_stream_write(
                target_path=target_path,
                temp_path=temp_path,
                record_count=record_count,
            )
            return record_count, uncompressed_size
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
        """
        Write an uncompressed JSON Lines copy of the records to the bronze path.
        
        Parameters
        ----------
        records : list[bytes]
            JSON Lines records to write.
        provider : str
            Data provider identifier.
        entity : str
            Entity identifier.
        date_str : str
            Date component used to construct the destination filename.
        batch_id : BatchID
            Batch identifier used to construct the destination filename.
        
        Notes
        -----
        The destination is written atomically. An existing file with identical
        contents is accepted; a differing existing file raises ``FileExistsError``.
        """

        def _write() -> None:
            """
            Write the batch records to the resolved bronze JSONL path.
            
            Raises
            ------
            FileExistsError
                If the destination exists with different content.
            """
            json_filename = f"batch_{date_str}_{batch_id}.jsonl"
            json_relative_path = self._resolve_bronze_path(
                provider, entity, date_str, json_filename
            )

            jsonl_content = b"".join(records)

            json_full_path = self.base_path / json_relative_path
            write_bytes_if_absent_or_same(
                json_full_path,
                jsonl_content,
                mismatch_message=(
                    "Bronze JSON copy already exists with different payload: "
                    f"{json_full_path}"
                ),
            )

        await asyncio.to_thread(_write)


def _existing_payload_matches(
    target_path: Path,
    candidate_path: Path,
    matches: Callable[[Path, Path], bool],
) -> bool:
    return target_path.exists() and matches(target_path, candidate_path)


def _publish_new_file_exclusive(source: Path, target: Path) -> None:
    """Publish a completed file at the target path without overwriting it.
    
    Parameters
    ----------
    source : pathlib.Path
        Temporary file to link to the target.
    target : pathlib.Path
        Destination path, which must not already exist.
    
    Raises
    ------
    FileExistsError
        If the target path already exists because a concurrent writer created it first.
    OSError
        If the hard link cannot be created for another reason.
    
    Notes
    -----
    The source file is removed after linking when possible.
    """
    try:
        os.link(os.fspath(source), os.fspath(target))
    except OSError as exc:
        if exc.errno == errno.EEXIST and not isinstance(exc, FileExistsError):
            raise FileExistsError(*exc.args) from exc
        raise
    with contextlib.suppress(OSError):
        source.unlink()


def write_bytes_if_absent_or_same(
    target: Path, data: bytes, *, mismatch_message: str
) -> None:
    """Write bytes to a target only if it is absent or already contains the same data.
    
    Parameters
    ----------
    target : pathlib.Path
        Destination path.
    data : bytes
        Complete byte payload to publish.
    mismatch_message : str
        Message for the ``FileExistsError`` raised when the target contains
        different bytes.
    
    Raises
    ------
    FileExistsError
        If the target exists with different contents.
    
    Notes
    -----
    Creates the target's parent directories as needed and removes temporary files
    after publication or failure.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp",
        prefix="." + target.stem + "_",
        dir=target.parent,
    )
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        try:
            _publish_new_file_exclusive(temp_path, target)
        except FileExistsError:
            if target.read_bytes() != data:
                raise FileExistsError(mismatch_message) from None
    finally:
        with contextlib.suppress(OSError):
            if temp_path.exists():
                temp_path.unlink()


__all__ = ["BronzeWriterIOMixin"]
