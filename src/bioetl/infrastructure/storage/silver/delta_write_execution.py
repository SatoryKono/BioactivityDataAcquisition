"""Plain Delta write and schema-evolution helpers for Silver writes."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from typing import Any, cast

from deltalake import DeltaTable as DeltaTableType

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.delta_request_models import (
    _DeltaWriteRequest,
)

__all__ = [
    "_build_plain_delta_write_kwargs",
    "_evolve_delta_schema_with_empty_append",
    "_is_duplicate_field_name_schema_error",
    "_load_delta_table",
    "_write_plain_delta_request",
]

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
        except BaseException as exc:  # pragma: no cover - surfaced through await
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
        "table_or_uri": request.table_path,
        "data": request.arrow_data,
        "mode": mode,
        "partition_by": request.partition_cols,
    }
    if schema_mode is not None:
        kwargs["schema_mode"] = schema_mode
    return kwargs


async def _write_plain_delta_request(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    request: _DeltaWriteRequest,
    mode: str,
    schema_mode: str | None = None,
    timeout_seconds: float = 60.0,
) -> None:
    """Execute a non-merge Delta write for an already prepared request."""
    kwargs = _build_plain_delta_write_kwargs(
        request,
        mode=mode,
        schema_mode=schema_mode,
    )
    try:
        await _await_blocking_deltalake_call(
            operation_name="plain-write",
            call=lambda: load_module().write_deltalake(**kwargs),
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
    updated_request: _DeltaWriteRequest = cast(  # type: ignore[redundant-cast]
        _DeltaWriteRequest,
        replace(request, merge_schema=False),
    )
    return updated_request


async def _load_delta_table(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    table_path: str,
) -> DeltaTableType:
    """Load a Delta table asynchronously for merge execution."""
    return await _await_blocking_deltalake_call(
        operation_name="load-table",
        call=lambda: load_module().DeltaTable(table_path),
    )
