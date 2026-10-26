"""Plain Delta write and schema-evolution helpers for Silver writes."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess  # nosec B404 - see suppression registry
import sys
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import IO, Any, Protocol, cast

import pyarrow as pa
from deltalake import DeltaTable as DeltaTableType

from bioetl.domain.locking import register_lock_release_barrier
from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
)
from bioetl.infrastructure.storage.silver.delta_request_models import (
    _DeltaWriteRequest,
)
from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_bytes

__all__ = [
    "_build_plain_delta_write_kwargs",
    "_evolve_delta_schema_with_empty_append",
    "_is_duplicate_field_name_schema_error",
    "_load_delta_table",
    "_write_plain_delta_request",
]

_PLAIN_DELTA_WRITE_SUBPROCESS_CODE = (
    "import json\n"
    "import sys\n"
    "from pathlib import Path\n"
    "import pyarrow.ipc as ipc\n"
    "from deltalake import write_deltalake\n"
    "metadata = json.loads(sys.argv[1])\n"
    "arrow_path = Path(metadata['arrow_path'])\n"
    "with arrow_path.open('rb') as handle:\n"
    "    table = ipc.open_stream(handle).read_all()\n"
    "table_path = Path(metadata['table_or_uri']).expanduser().resolve()\n"
    "table_path.parent.mkdir(parents=True, exist_ok=True)\n"
    "kwargs = {\n"
    "    'table_or_uri': table_path.as_posix(),\n"
    "    'data': table,\n"
    "    'mode': metadata['mode'],\n"
    "}\n"
    "if metadata.get('partition_by'):\n"
    "    kwargs['partition_by'] = metadata['partition_by']\n"
    "if metadata.get('schema_mode') is not None:\n"
    "    kwargs['schema_mode'] = metadata['schema_mode']\n"
    "write_deltalake(**kwargs)\n"
)


def _require_delta_write_request(value: object) -> _DeltaWriteRequest:
    """Return a concrete Delta request after validating replacement output."""
    if not isinstance(value, _DeltaWriteRequest):
        raise TypeError("dataclass replacement did not preserve _DeltaWriteRequest")
    return value


def _build_result_publishers[BlockingResult](
    result_future: asyncio.Future[BlockingResult],
) -> tuple[Callable[[BlockingResult], None], Callable[[BaseException], None]]:
    """Publish a daemon-thread result onto the awaiting event loop."""

    def _publish_result(result: BlockingResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    def _publish_exception(exc: BaseException) -> None:
        if not result_future.done():
            result_future.set_exception(exc)

    return _publish_result, _publish_exception


def _build_blocking_worker[BlockingResult](
    *,
    call: Callable[[], BlockingResult],
    loop: asyncio.AbstractEventLoop,
    publish_result: Callable[[BlockingResult], None],
    publish_exception: Callable[[BaseException], None],
) -> Callable[[], None]:
    """Run one blocking Delta call and publish its outcome to the loop."""

    def _worker() -> None:
        try:
            result = call()
        # pragma: no cover - surfaced through await
        # NOSONAR python:S5754 - thread boundary must capture all call failures
        except Exception as exc:
            with suppress(RuntimeError):
                loop.call_soon_threadsafe(publish_exception, exc)
            return
        with suppress(RuntimeError):
            loop.call_soon_threadsafe(publish_result, result)

    return _worker


def _lock_release_join_barrier(
    worker: threading.Thread,
) -> Callable[[], Awaitable[None]]:
    """Return a barrier that joins a Delta worker before lock release.

    The join has no timeout. ``release_lock`` must not drop the lock while
    this thread can still commit. A stuck native call holds the lock until
    the thread returns; the caller-facing timeout still completes immediately.
    """

    async def _join_worker() -> None:
        await asyncio.to_thread(worker.join)

    return _join_worker


async def _await_blocking_deltalake_call[BlockingResult](
    *,
    operation_name: str,
    call: Callable[[], BlockingResult],
    timeout_seconds: float | None = None,
) -> BlockingResult:
    """Run one blocking Delta Lake call on a daemon thread.

    ``asyncio.run_in_executor`` keeps the default executor thread alive even
    after ``wait_for`` times out. On Windows, a hung Rust Delta write can then
    stall pytest/loop shutdown long after the inner timeout has fired. A
    dedicated daemon thread keeps the timeout bounded without coupling loop
    teardown to the blocked native call.

    When a lock hold has armed release barriers, the worker is joined before
    that lock is released. The timeout itself still returns without waiting.
    """
    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[BlockingResult] = loop.create_future()
    publish_result, publish_exception = _build_result_publishers(result_future)
    worker = threading.Thread(
        target=_build_blocking_worker(
            call=call,
            loop=loop,
            publish_result=publish_result,
            publish_exception=publish_exception,
        ),
        name=f"bioetl-deltalake-{operation_name}",
        daemon=True,
    )
    worker.start()
    register_lock_release_barrier(_lock_release_join_barrier(worker))

    try:
        if timeout_seconds is None:
            return await result_future
        return await asyncio.wait_for(result_future, timeout=timeout_seconds)
    except TimeoutError:
        result_future.cancel()
        raise


def _build_plain_delta_write_kwargs(
    request: _DeltaWriteRequest,
    *,
    mode: str,
    schema_mode: str | None = None,
) -> dict[str, Any]:  # Any: Delta Lake write kwargs are heterogeneous
    """Build keyword arguments for a non-merge Delta write."""
    kwargs: dict[str, Any] = {  # Any: heterogeneous kwargs dict
        "table_or_uri": normalize_delta_filesystem_path(request.table_path),
        "data": request.arrow_data,
        "mode": mode,
    }
    if request.partition_cols:
        kwargs["partition_by"] = request.partition_cols
    if schema_mode is not None:
        kwargs["schema_mode"] = schema_mode
    return kwargs


def _ensure_delta_table_parent_dir(table_path: str) -> None:
    """Create the parent directory for a local Delta table before first write."""
    normalized = str(table_path).replace("\\", "/")
    if "://" in normalized:
        return
    Path(normalized).parent.mkdir(parents=True, exist_ok=True)


def _serialize_arrow_table_for_subprocess(table: pa.Table) -> bytes:
    """Serialize an Arrow table for a one-shot Delta writer subprocess."""
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return bytes(sink.getvalue())


def _write_arrow_payload_for_subprocess(*, table_path: str, table: pa.Table) -> Path:
    """Persist one Arrow IPC payload for a child-process Delta write.

    Passing large payloads through ``subprocess.run(..., input=...)`` can deadlock
    on Windows when the child has not started reading stdin yet. A temp file keeps
    the parent/child contract bounded without coupling to pipe buffer sizes.
    """
    canonical = normalize_delta_filesystem_path(table_path)
    if "://" in canonical.replace("\\", "/"):
        payload_dir = Path(tempfile.gettempdir())
    else:
        payload_dir = Path(canonical).parent
        payload_dir.mkdir(parents=True, exist_ok=True)
    fd, payload_path_str = tempfile.mkstemp(
        suffix=".arrow",
        prefix=".plain_delta_payload_",
        dir=payload_dir,
    )
    os.close(fd)
    payload_path = Path(payload_path_str)
    atomic_write_bytes(payload_path, _serialize_arrow_table_for_subprocess(table))
    return payload_path


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


def _readers_still_running(readers: tuple[_BoundedStreamReader, ...]) -> bool:
    return any(reader.is_alive() for reader in readers)


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
    if _readers_still_running(reader_tuple):
        _close_subprocess_pipes(proc)
        _join_bounded_readers(
            reader_tuple,
            timeout_seconds=_SUBPROCESS_READER_JOIN_SECONDS,
        )
    _close_subprocess_pipes(proc)


def _decode_subprocess_output(payload: bytes) -> str:
    """Decode bounded subprocess output for deterministic error messages."""
    return payload.decode("utf-8", errors="replace").strip()[-4000:]


def _run_plain_delta_write_subprocess(
    *,
    kwargs: dict[str, Any],  # Any: Delta Lake write kwargs are heterogeneous
    arrow_data: pa.Table,
    timeout_seconds: float,
    cancel_event: threading.Event | None = None,
) -> None:
    """Execute one plain Delta write in a child process.

    This path is used by Windows E2E runs where a hung delta-rs native call can
    outlive Python thread timeouts. The child process keeps the timeout
    enforceable without changing the default production write path.

    Stdout and stderr are drained concurrently and only the last 16384 bytes
    are retained. Pipes are closed before the readers are joined, and that
    join is bounded, so a child that leaves a pipe open cannot extend the
    timeout. ``cancel_event`` is polled while waiting. The plain-write caller
    sets it when the awaiting task is cancelled, which reaps the child
    without waiting out ``timeout_seconds``.
    """
    table_or_uri = str(kwargs["table_or_uri"])
    metadata = {key: value for key, value in kwargs.items() if key != "data"}
    payload_path = _write_arrow_payload_for_subprocess(
        table_path=table_or_uri,
        table=arrow_data,
    )
    metadata["arrow_path"] = payload_path.as_posix()
    try:
        # No shell or user-controlled command is involved.
        proc = subprocess.Popen(  # nosec B603 - see suppression registry
            [
                sys.executable,
                "-c",
                _PLAIN_DELTA_WRITE_SUBPROCESS_CODE,
                json.dumps(metadata),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out_reader = _BoundedStreamReader(proc.stdout)
        err_reader = _BoundedStreamReader(proc.stderr)
        out_reader.start()
        err_reader.start()
        timeout_exc: subprocess.TimeoutExpired | None = None
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
            _finish_subprocess_readers(proc, out_reader, err_reader)
        if timeout_exc is not None:
            raise TimeoutError from timeout_exc
    finally:
        with suppress(OSError):
            payload_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        stderr = err_reader.get_decoded()
        stdout = out_reader.get_decoded()
        raise RuntimeError(
            "Delta write subprocess failed "
            f"(exit_code={proc.returncode}, stderr={stderr!r}, stdout={stdout!r})"
        )


def _should_execute_plain_write_inline(
    *,
    table_path: str,
    module: object,
) -> bool:
    """Return whether a plain Delta write should use the local inline path."""
    return (
        "://" not in table_path
        and getattr(module, "__name__", "")
        == "bioetl.infrastructure.storage.silver_writer"
    )


def _should_execute_delta_table_load_inline(
    *,
    table_path: str,
    module: object,
) -> bool:
    """Return whether a DeltaTable load should use the local inline path."""
    return _should_execute_plain_write_inline(table_path=table_path, module=module)


class _DeltaWriteModule(Protocol):
    def write_deltalake(
        self,
        **kwargs: Any,  # Any: upstream Delta API accepts heterogeneous values.
    ) -> None:
        """Write a Delta table using the runtime module."""
        ...


def _run_plain_delta_write_inline(
    *,
    module: _DeltaWriteModule,
    kwargs: dict[str, Any],  # Any: Delta Lake write kwargs are heterogeneous
    timeout_seconds: float,
) -> None:
    """Execute a local plain Delta write without thread offload.

    Inline writes run in-process and cannot be cancelled mid-call (native
    delta-rs). Do **not** convert a completed write into ``TimeoutError`` based
    on elapsed wall time: that fails the pipeline after durable data is already
    committed (common on slow/network filesystems such as Google Drive mounts).
    Hard cancellation remains available on the thread/process offload paths.
    """
    del timeout_seconds  # budget applies only to cancellable offload paths
    module.write_deltalake(**kwargs)


async def _write_plain_delta_request(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    request: _DeltaWriteRequest,
    mode: str,
    schema_mode: str | None = None,
    timeout_seconds: float = 60.0,
    process_isolation: bool = False,
) -> None:
    """Execute a non-merge Delta write for an already prepared request."""
    canonical_path = normalize_delta_filesystem_path(request.table_path)
    _ensure_delta_table_parent_dir(canonical_path)
    request = replace(request, table_path=canonical_path)
    kwargs = _build_plain_delta_write_kwargs(
        request,
        mode=mode,
        schema_mode=schema_mode,
    )
    try:
        if process_isolation:
            cancel_event = threading.Event()
            try:
                await _await_blocking_deltalake_call(
                    operation_name="plain-write-subprocess",
                    call=lambda: _run_plain_delta_write_subprocess(
                        kwargs=kwargs,
                        arrow_data=request.arrow_data,
                        timeout_seconds=timeout_seconds,
                        cancel_event=cancel_event,
                    ),
                    timeout_seconds=timeout_seconds + 5.0,
                )
            except asyncio.CancelledError:
                cancel_event.set()
                raise
            return
        module = load_module()
        if _should_execute_plain_write_inline(table_path=canonical_path, module=module):
            _run_plain_delta_write_inline(
                module=module,
                kwargs=kwargs,
                timeout_seconds=timeout_seconds,
            )
            return
        await _await_blocking_deltalake_call(
            operation_name="plain-write",
            call=lambda: module.write_deltalake(**kwargs),
            timeout_seconds=timeout_seconds,
        )
    except TimeoutError as exc:
        raise TimeoutError(
            f"Delta write timed out after {timeout_seconds}s for table {request.table_path}"
        ) from exc


def _is_duplicate_field_name_schema_error(exc: BaseException) -> bool:
    """Return whether an exception matches the known duplicate-field quirk."""
    return "Duplicate field name:" in str(exc)


async def _evolve_delta_schema_with_empty_append(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    request: _DeltaWriteRequest,
) -> _DeltaWriteRequest:
    """Pre-evolve an existing Delta table schema without writing extra rows."""
    empty_request = _require_delta_write_request(
        replace(
            request,
            validated_mode=SilverWriteMode.APPEND,
            arrow_data=request.arrow_data.slice(0, 0),
            schema_mode="merge",
        )
    )
    await _write_plain_delta_request(
        load_module=load_module,
        request=empty_request,
        mode="append",
        schema_mode="merge",
    )
    return _require_delta_write_request(replace(request, merge_schema=False))


async def _load_delta_table(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    table_path: str,
) -> DeltaTableType:
    """Load a Delta table asynchronously for merge execution."""
    module = load_module()
    if _should_execute_delta_table_load_inline(table_path=table_path, module=module):
        return cast("DeltaTableType", module.DeltaTable(table_path))
    return cast(
        "DeltaTableType",
        await _await_blocking_deltalake_call(
            operation_name="load-table",
            call=lambda: module.DeltaTable(table_path),
        ),
    )
