"""Request models and dispatch helpers for Silver Delta writes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import NoReturn

import pyarrow as pa
from deltalake.exceptions import DeltaError, SchemaMismatchError

from bioetl.domain.exceptions import MergeConflictError, SchemaViolationError
from bioetl.domain.medallion import SilverWriteMode

__all__ = [
    "_DeltaWriteDispatchPolicy",
    "_DeltaWriteHandler",
    "_DeltaWriteRequest",
    "_build_dispatch_policy",
    "_dispatch_request_by_mode",
    "_dispatch_request_with_domain_errors",
    "_raise_domain_write_error",
    "_select_dispatch_handler",
]


@dataclass(frozen=True, slots=True)
class _DeltaWriteRequest:
    """Normalized request object for a single Silver Delta write dispatch."""

    validated_mode: SilverWriteMode
    table_path: str
    arrow_data: pa.Table
    primary_keys: list[str]
    partition_cols: list[str] | None
    schema_mode: str | None = None
    merge_schema: bool = False
    # Stable identity for deterministic retry jitter across concurrent writes.
    operation_id: str = ""


_DeltaWriteHandler = Callable[[_DeltaWriteRequest], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class _DeltaWriteDispatchPolicy:
    """Mode-to-handler policy for a normalized Delta write request."""

    write_delete: _DeltaWriteHandler
    write_append: _DeltaWriteHandler
    write_merge: _DeltaWriteHandler


def _raise_domain_write_error(
    *,
    table_name: str,
    exc: SchemaMismatchError | pa.ArrowTypeError | DeltaError,
) -> NoReturn:
    """Translate Delta-layer write failures to domain errors when applicable."""
    if isinstance(exc, (SchemaMismatchError, pa.ArrowTypeError)):
        raise SchemaViolationError(table_name, errors=[str(exc)]) from exc
    if "Merge-conflict" in str(exc):
        raise MergeConflictError(table_name, conflicts=1) from exc
    raise exc


def _build_dispatch_policy(
    *,
    write_delete: _DeltaWriteHandler,
    write_append: _DeltaWriteHandler,
    write_merge: _DeltaWriteHandler,
) -> _DeltaWriteDispatchPolicy:
    """Build the Delta write dispatch policy for a writer instance."""
    return _DeltaWriteDispatchPolicy(
        write_delete=write_delete,
        write_append=write_append,
        write_merge=write_merge,
    )


def _select_dispatch_handler(
    *,
    validated_mode: SilverWriteMode,
    policy: _DeltaWriteDispatchPolicy,
) -> _DeltaWriteHandler:
    """Select the mode-specific write handler from the dispatch policy."""
    if validated_mode == SilverWriteMode.DELETE:
        return policy.write_delete
    if validated_mode == SilverWriteMode.APPEND:
        return policy.write_append
    return policy.write_merge


async def _dispatch_request_by_mode(
    *,
    request: _DeltaWriteRequest,
    policy: _DeltaWriteDispatchPolicy,
) -> None:
    """Dispatch a normalized Delta write request to the mode-specific handler."""
    handler = _select_dispatch_handler(
        validated_mode=request.validated_mode,
        policy=policy,
    )
    await handler(request)


async def _dispatch_request_with_domain_errors(
    *,
    table_name: str,
    request: _DeltaWriteRequest,
    dispatch_write: _DeltaWriteHandler,
) -> None:
    """Execute a Delta write dispatch and translate storage exceptions."""
    try:
        await dispatch_write(request)
    except (SchemaMismatchError, pa.ArrowTypeError, DeltaError) as exc:
        _raise_domain_write_error(table_name=table_name, exc=exc)
