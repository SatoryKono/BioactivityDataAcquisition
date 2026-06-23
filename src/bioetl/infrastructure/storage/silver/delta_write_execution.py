"""Plain Delta write and schema-evolution helpers for Silver writes."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
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
    loop = asyncio.get_running_loop()
    write_future = loop.run_in_executor(
        None,
        lambda: load_module().write_deltalake(**kwargs),
    )
    try:
        await asyncio.wait_for(write_future, timeout=timeout_seconds)
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
    loop = asyncio.get_running_loop()
    empty_request: _DeltaWriteRequest = cast(  # type: ignore[redundant-cast]
        _DeltaWriteRequest,
        replace(
            request,
            validated_mode=SilverWriteMode.APPEND,
            arrow_data=request.arrow_data.slice(0, 0),
            schema_mode="merge",
        ),
    )
    await loop.run_in_executor(
        None,
        lambda: load_module().write_deltalake(
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
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: load_module().DeltaTable(table_path),
    )
