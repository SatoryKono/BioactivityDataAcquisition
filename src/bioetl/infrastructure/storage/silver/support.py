"""Support utilities for Silver layer operations."""

from __future__ import annotations

import asyncio
import subprocess  # nosec B404 - see suppression registry
import threading
import time
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import IO

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.delta.schema_ops import (
    delta_schema_to_pyarrow,
    drop_nondeterministic_persisted_fields,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
    resolve_delta_table_path,
)

__all__ = [
    "get_table_schema",
    "prepare_arrow_data",
    "resolve_table_path",
]

# Create a shared ArrowDataConverter instance for the prepare_arrow_data function
_arrow_converter = ArrowDataConverter()


def resolve_table_path(
    base_path: str | Path, table_name: str, flat_structure: bool = False
) -> str:
    """Resolve the filesystem path for a Delta table.

    Args:
        base_path: Base path for Delta tables.
        table_name: Table name in dot notation (e.g., 'chembl.activity').
        flat_structure: If True, returns base_path directly.

    Returns:
        String path to the table directory.
    """
    return resolve_delta_table_path(
        base_path=str(base_path),
        table_name=table_name,
        flat_structure=flat_structure,
    )


async def get_table_schema(base_path: str | Path, table_name: str) -> pa.Schema | None:
    """Get existing table schema if table exists.

    Retrieves the PyArrow schema from an existing Delta table.
    Used for schema evolution checks and validation.

    Args:
        base_path: Base path for Delta tables.
        table_name: Table name in dot notation (e.g., 'chembl.activity').

    Returns:
        PyArrow Schema if table exists, None otherwise.
    """
    table_path = resolve_table_path(base_path, table_name)

    def _sync_get_schema() -> pa.Schema | None:
        try:
            # Load the Delta table
            dt = DeltaTable(normalize_delta_filesystem_path(table_path))
            return delta_schema_to_pyarrow(dt.schema())
        except TableNotFoundError:
            return None
        except Exception:
            # Handle other potential errors (permission issues, corrupt tables, etc.)
            return None

    return await asyncio.to_thread(_sync_get_schema)


def prepare_arrow_data(
    records: list[dict[str, object]],
    schema: pa.Schema,
    primary_keys: list[str],
    column_order: list[str] | None = None,
) -> pa.Table:
    """Prepare Arrow table from records with schema filtering and sorting.

    This is a standalone version of the method from SilverWriterArrowMixin.

    Args:
        records: List of record dictionaries to convert.
        schema: PyArrow schema defining target field types.
        primary_keys: List of column names used for ascending sort order.
        column_order: Optional explicit column ordering; uses canonical order if None.

    Returns:
        PyArrow Table filtered to schema columns, ordered, and sorted by primary keys.
    """
    # Convert records to Arrow table using the shared converter
    arrow_table = _arrow_converter.convert_records_to_arrow_with_schema(
        records,
        schema,
        primary_keys=primary_keys,
        column_order=column_order,
    )

    # Apply schema filtering to drop nondeterministic persisted fields
    filtered_table = drop_nondeterministic_persisted_fields(arrow_table)

    return filtered_table


_SUBPROCESS_OUTPUT_LIMIT_BYTES = 16384
_SUBPROCESS_OUTPUT_CHAR_LIMIT = 4000
_SUBPROCESS_READER_DRAIN_SECONDS = 0.5
_SUBPROCESS_READER_JOIN_SECONDS = 2.0
_SUBPROCESS_CANCEL_POLL_SECONDS = 0.2


class _BoundedStreamReader(threading.Thread):
    """Drain a stream concurrently while retaining only a bounded tail."""

    def __init__(
        self,
        stream: IO[bytes] | None,
        limit_bytes: int = _SUBPROCESS_OUTPUT_LIMIT_BYTES,
    ) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._limit = limit_bytes
        self._chunks: list[bytes] = []
        self._length = 0
        self._lock = threading.Lock()

    def run(self) -> None:
        stream = self._stream
        if stream is None:
            return
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                self._append_bounded(chunk)
        except (OSError, ValueError):
            return

    def _append_bounded(self, chunk: bytes) -> None:
        with self._lock:
            self._chunks.append(chunk)
            self._length += len(chunk)
            while self._chunks and self._length - len(self._chunks[0]) >= self._limit:
                removed = self._chunks.pop(0)
                self._length -= len(removed)

    def get_decoded(self, char_limit: int = _SUBPROCESS_OUTPUT_CHAR_LIMIT) -> str:
        """Decode the retained tail and return up to `char_limit` characters."""
        with self._lock:
            payload = b"".join(self._chunks)[-self._limit :]
        return payload.decode("utf-8", errors="replace").strip()[-char_limit:]


def _wait_for_plain_delta_subprocess(
    proc: subprocess.Popen[bytes],
    *,
    timeout_seconds: float,
    cancel_event: threading.Event | None,
) -> None:
    """Wait until the child exits, the deadline passes, or cancellation is set."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if cancel_event is not None and cancel_event.is_set():
            raise subprocess.TimeoutExpired(cmd=proc.args, timeout=timeout_seconds)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd=proc.args, timeout=timeout_seconds)
        slice_timeout = (
            min(_SUBPROCESS_CANCEL_POLL_SECONDS, remaining)
            if cancel_event is not None
            else remaining
        )
        try:
            proc.wait(timeout=slice_timeout)
        except subprocess.TimeoutExpired:
            timed_out_fully = cancel_event is None or slice_timeout >= remaining - 1e-9
            if timed_out_fully:
                raise
            continue
        else:
            return


def _reap_plain_delta_subprocess(proc: subprocess.Popen[bytes]) -> None:
    """Kill a child that is still running after the wait returns."""
    if proc.returncode is not None:
        return
    with suppress(OSError):
        proc.kill()
    with suppress(subprocess.TimeoutExpired, OSError):
        proc.wait(timeout=_SUBPROCESS_READER_JOIN_SECONDS)


def _close_subprocess_pipes(proc: subprocess.Popen[bytes]) -> None:
    for stream in (proc.stdout, proc.stderr):
        if stream is None:
            continue
        with suppress(OSError, ValueError):
            stream.close()


def _join_bounded_readers(
    readers: tuple[_BoundedStreamReader, ...],
    *,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    pending = list(readers)
    while pending and time.monotonic() < deadline:
        still_running: list[_BoundedStreamReader] = []
        for reader in pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                still_running.extend(pending[pending.index(reader) :])
                break
            reader.join(timeout=min(0.01, remaining))
            if reader.is_alive():
                still_running.append(reader)
        pending = still_running


def _finish_subprocess_readers(
    proc: subprocess.Popen[bytes],
    *readers: _BoundedStreamReader,
) -> None:
    """Drain captured output, then close pipes that are still blocking."""
    reader_tuple = tuple(readers)
    _join_bounded_readers(
        reader_tuple,
        timeout_seconds=_SUBPROCESS_READER_DRAIN_SECONDS,
    )
    if any(reader.is_alive() for reader in reader_tuple):
        _close_subprocess_pipes(proc)
        _join_bounded_readers(
            reader_tuple,
            timeout_seconds=_SUBPROCESS_READER_JOIN_SECONDS,
        )
    _close_subprocess_pipes(proc)


def _execute_bounded_subprocess(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    cancel_event: threading.Event | None,
) -> None:
    """Run a fixed argv and keep only a bounded tail of both pipes.

    ``bufsize=0`` leaves the pipes unbuffered so ``close()`` cannot block on
    the ``BufferedReader`` lock while a reader thread is inside ``read()``.
    Reader threads start inside the cleanup block: a ``start()`` failure
    still reaps the child.
    """
    # No shell or user-controlled command is involved.
    proc = subprocess.Popen(  # nosec B603 - see suppression registry
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    out_reader = _BoundedStreamReader(proc.stdout)
    err_reader = _BoundedStreamReader(proc.stderr)
    started: list[_BoundedStreamReader] = []
    timeout_exc: subprocess.TimeoutExpired | None = None
    try:
        out_reader.start()
        started.append(out_reader)
        err_reader.start()
        started.append(err_reader)
        try:
            _wait_for_plain_delta_subprocess(
                proc,
                timeout_seconds=timeout_seconds,
                cancel_event=cancel_event,
            )
        except subprocess.TimeoutExpired as exc:
            timeout_exc = exc
    finally:
        _reap_plain_delta_subprocess(proc)
        if started:
            _finish_subprocess_readers(proc, *started)
        else:
            _close_subprocess_pipes(proc)
    if timeout_exc is not None:
        raise TimeoutError from timeout_exc
    if proc.returncode != 0:
        stderr = err_reader.get_decoded() if err_reader in started else ""
        stdout = out_reader.get_decoded() if out_reader in started else ""
        raise RuntimeError(
            "Delta write subprocess failed "
            f"(exit_code={proc.returncode}, stderr={stderr!r}, stdout={stdout!r})"
        )
