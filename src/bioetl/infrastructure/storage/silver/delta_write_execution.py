"""Plain Delta write and schema-evolution helpers for Silver writes."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess  # nosec B404
import sys
import tempfile
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol, cast

import pyarrow as pa
from deltalake import DeltaTable as DeltaTableType

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
    """
    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[BlockingResult] = loop.create_future()

    def _publish_result(result: BlockingResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    def _publish_exception(exc: BaseException) -> None:
        if not result_future.done():
            result_future.set_exception(exc)

    def _worker() -> None:
        try:
            result = call()
        except Exception as exc:  # pragma: no cover - surfaced through await  # NOSONAR python:S5754 - thread boundary must capture all call failures
            with suppress(RuntimeError):
                loop.call_soon_threadsafe(_publish_exception, exc)
            return
        with suppress(RuntimeError):
            loop.call_soon_threadsafe(_publish_result, result)

    worker = threading.Thread(
        target=_worker,
        name=f"bioetl-deltalake-{operation_name}",
        daemon=True,
    )
    worker.start()

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
    """Create the parent directory for a Delta table before first write."""
    Path(table_path).parent.mkdir(parents=True, exist_ok=True)


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
    payload_dir = Path(normalize_delta_filesystem_path(table_path)).parent
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


def _decode_subprocess_output(payload: bytes) -> str:
    """Decode bounded subprocess output for deterministic error messages."""
    return payload.decode("utf-8", errors="replace").strip()[-4000:]


def _run_plain_delta_write_subprocess(
    *,
    kwargs: dict[str, Any],  # Any: Delta Lake write kwargs are heterogeneous
    arrow_data: pa.Table,
    timeout_seconds: float,
) -> None:
    """Execute one plain Delta write in a child process.

    This path is used by Windows E2E runs where a hung delta-rs native call can
    outlive Python thread timeouts. The child process keeps the timeout
    enforceable without changing the default production write path.
    """
    table_or_uri = str(kwargs["table_or_uri"])
    metadata = {key: value for key, value in kwargs.items() if key != "data"}
    payload_path = _write_arrow_payload_for_subprocess(
        table_path=table_or_uri,
        table=arrow_data,
    )
    metadata["arrow_path"] = payload_path.as_posix()
    try:
        try:
            # No shell or user-controlled command is involved.
            completed = subprocess.run(  # nosec B603
                [
                    sys.executable,
                    "-c",
                    _PLAIN_DELTA_WRITE_SUBPROCESS_CODE,
                    json.dumps(metadata),
                ],
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError from exc
    finally:
        with suppress(OSError):
            payload_path.unlink(missing_ok=True)

    if completed.returncode != 0:
        stderr = _decode_subprocess_output(completed.stderr)
        stdout = _decode_subprocess_output(completed.stdout)
        raise RuntimeError(
            "Delta write subprocess failed "
            f"(exit_code={completed.returncode}, stderr={stderr!r}, stdout={stdout!r})"
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
    """Execute a local plain Delta write without thread offload."""
    started_at = asyncio.get_running_loop().time()
    module.write_deltalake(**kwargs)
    if asyncio.get_running_loop().time() - started_at > timeout_seconds:
        raise TimeoutError


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
            await _await_blocking_deltalake_call(
                operation_name="plain-write-subprocess",
                call=lambda: _run_plain_delta_write_subprocess(
                    kwargs=kwargs,
                    arrow_data=request.arrow_data,
                    timeout_seconds=timeout_seconds,
                ),
                timeout_seconds=timeout_seconds + 5.0,
            )
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
    empty_request: _DeltaWriteRequest = cast(  # type: ignore[redundant-cast]
        _DeltaWriteRequest,
        replace(
            request,
            validated_mode=SilverWriteMode.APPEND,
            arrow_data=request.arrow_data.slice(0, 0),
            schema_mode="merge",
        ),
    )
    await _await_blocking_deltalake_call(
        operation_name="schema-evolve",
        call=lambda: load_module().write_deltalake(
            **_build_plain_delta_write_kwargs(
                empty_request,
                mode="append",
                schema_mode="merge",
            )
        ),
    )
    updated_request = cast(_DeltaWriteRequest, replace(request, merge_schema=False))
    return updated_request


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
