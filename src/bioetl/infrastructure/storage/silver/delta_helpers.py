"""Helper utilities for Silver Delta write dispatch and merge orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, NoReturn, cast

import pyarrow as pa
from deltalake.exceptions import DeltaError, SchemaMismatchError

from bioetl.domain.exceptions import (
    MergeConflictError,
    SchemaViolationError,
)
from bioetl.domain.medallion import SilverWriteMode

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort


class _MergeExecutionTimeoutError(RuntimeError):
    """Internal timeout marker used for merge retry orchestration."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Merge execution timed out after {timeout_seconds}s")


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


_DeltaWriteHandler = Callable[[_DeltaWriteRequest], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class _DeltaWriteDispatchPolicy:
    """Mode-to-handler policy for a normalized Delta write request."""

    write_delete: _DeltaWriteHandler
    write_append: _DeltaWriteHandler
    write_merge: _DeltaWriteHandler


_MERGE_UPDATE_POLICY = "content_hash_only"


def _build_content_changed_predicate(
    source_alias: str = "source",
    target_alias: str = "target",
) -> str:
    """Build a null-safe content-hash change predicate."""
    return (
        f"{source_alias}.content_hash <> {target_alias}.content_hash "
        f"OR ({source_alias}.content_hash IS NULL AND {target_alias}.content_hash IS NOT NULL) "
        f"OR ({source_alias}.content_hash IS NOT NULL AND {target_alias}.content_hash IS NULL)"
    )


def _build_merge_update_predicate(records: pa.Table | pa.RecordBatchReader) -> str:
    """Build the Silver merge update predicate for rerun-safe writes.

    Silver/Gold physical Delta rows intentionally exclude occurrence-scoped runtime
    anchors such as ``_run_type`` via ``drop_nondeterministic_persisted_fields``.
    Row-level update decisions therefore remain content-hash based; rebuild/backfill
    semantics are enforced by lifecycle cleanup and exclusive locks, not by a
    run-type precedence predicate inside the persisted Delta merge.
    """
    schema = records.schema
    if "content_hash" not in schema.names:
        return "true"

    content_changed = _build_content_changed_predicate()
    return content_changed


def _build_merge_condition(primary_keys: list[str]) -> str:
    """Build Delta merge predicate from primary key columns."""
    return " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)


def _build_merge_execute_callable(
    *,
    dt: DeltaTableType,
    records: pa.Table | pa.RecordBatchReader,
    merge_condition: str,
    merge_schema: bool,
) -> Callable[[], Any]:  # Any: Delta merge returns heterogeneous result
    """Build the blocking Delta merge callable for ``run_in_executor``."""

    def _execute() -> Any:  # Any: Delta merge returns heterogeneous result
        update_predicate = _build_merge_update_predicate(records)
        return (
            dt.merge(
                source=records,
                predicate=merge_condition,
                source_alias="source",
                target_alias="target",
                merge_schema=merge_schema,
            )
            .when_matched_update_all(predicate=update_predicate)
            .when_not_matched_insert_all()
            .execute()
        )

    return _execute


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


async def _write_plain_delta_request(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    request: _DeltaWriteRequest,
    mode: str,
    schema_mode: str | None = None,
) -> None:
    """Execute a non-merge Delta write for an already prepared request."""
    kwargs = _build_plain_delta_write_kwargs(
        request,
        mode=mode,
        schema_mode=schema_mode,
    )
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: load_module().write_deltalake(**kwargs),
    )


def _is_duplicate_field_name_schema_error(exc: BaseException) -> bool:
    """Return whether an exception matches the known duplicate-field quirk.

    Delta Lake may surface this schema-evolution failure either as ``DeltaError``
    or as a generic ``Exception`` depending on platform/runtime bindings.
    """
    return "Duplicate field name:" in str(exc)


async def _evolve_delta_schema_with_empty_append(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    request: _DeltaWriteRequest,
) -> _DeltaWriteRequest:
    """Pre-evolve an existing Delta table schema without writing extra rows."""
    loop = asyncio.get_running_loop()
    empty_request = cast(
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
    return cast(_DeltaWriteRequest, replace(request, merge_schema=False))


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


async def _merge_records_with_timeout(
    *,
    logger: LoggerPort,
    dt: DeltaTableType,
    records: pa.Table | pa.RecordBatchReader,
    primary_keys: list[str],
    table_path: str,
    timeout_seconds: float,
    merge_schema: bool = False,
) -> None:
    """Execute Delta merge with timeout handling and structured timeout telemetry."""
    merge_condition = _build_merge_condition(primary_keys)
    loop = asyncio.get_running_loop()
    merge_future = loop.run_in_executor(
        None,
        _build_merge_execute_callable(
            dt=dt,
            records=records,
            merge_condition=merge_condition,
            merge_schema=merge_schema,
        ),
    )
    try:
        await asyncio.wait_for(
            merge_future,
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        logger.warning(
            "silver_merge_timeout",
            table_path=table_path,
            timeout_seconds=timeout_seconds,
            primary_keys=primary_keys,
        )
        raise _MergeExecutionTimeoutError(timeout_seconds) from exc
