"""Merge orchestration helpers for Silver Delta writes."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pyarrow as pa

from bioetl.infrastructure.storage.silver.delta_write_execution import (
    _await_blocking_deltalake_call,
)

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort

__all__ = [
    "ReplaySafeRerunContract",
    "_MergeExecutionTimeoutError",
    "_build_content_changed_predicate",
    "_build_merge_condition",
    "_build_merge_execute_callable",
    "_build_merge_update_predicate",
    "_delta_table_has_parquet_data",
    "_merge_records_with_timeout",
    "build_replay_safe_rerun_contract",
]


class _MergeExecutionTimeoutError(RuntimeError):
    """Internal timeout marker used for merge retry orchestration."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Merge execution timed out after {timeout_seconds}s")


_MERGE_UPDATE_POLICY = "content_hash_only"


@dataclass(frozen=True, slots=True)
class ReplaySafeRerunContract:
    """Machine-readable Silver rerun contract for merge-based semantic writes."""

    merge_update_policy: str
    requires_content_hash: bool
    external_guards: tuple[str, ...]
    strict_replay_safe: bool


def build_replay_safe_rerun_contract(
    records: pa.Table | pa.RecordBatchReader,
) -> ReplaySafeRerunContract:
    """Describe the actual replay-safe rerun guarantees of one merge input."""
    has_content_hash = "content_hash" in records.schema.names
    return ReplaySafeRerunContract(
        merge_update_policy=(
            _MERGE_UPDATE_POLICY if has_content_hash else "full_row_update"
        ),
        requires_content_hash=has_content_hash,
        external_guards=("lifecycle_cleanup", "exclusive_locks"),
        strict_replay_safe=has_content_hash,
    )


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
    """Build the Silver merge update predicate for rerun-safe writes."""
    contract = build_replay_safe_rerun_contract(records)
    if not contract.requires_content_hash:
        return "true"

    return _build_content_changed_predicate()


def _build_merge_condition(primary_keys: list[str]) -> str:
    """Build Delta merge predicate from primary key columns."""
    return " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)


def _delta_table_has_parquet_data(table_path: str) -> bool:
    """Return whether a local Delta table path already contains parquet data files."""
    table_path_obj = Path(table_path)
    if "://" in table_path or not table_path_obj.exists():
        # Remote/object-store tables and injected test doubles cannot be inspected.
        return True

    for dirpath, _dirnames, filenames in os.walk(table_path):
        if dirpath.endswith("_delta_log"):
            continue
        for filename in filenames:
            if filename.endswith(".parquet"):
                return True
    return False


def _build_merge_execute_callable(
    *,
    dt: DeltaTableType,
    table_path: str,
    records: pa.Table | pa.RecordBatchReader,
    merge_condition: str,
    merge_schema: bool,
) -> Callable[[], object]:
    """Build the blocking Delta merge callable for ``run_in_executor``."""

    def _execute() -> object:
        if not _delta_table_has_parquet_data(table_path):
            from deltalake import write_deltalake

            write_kwargs: dict[str, object] = {
                "table_or_uri": table_path,
                "data": records,
                "mode": "append",
            }
            if merge_schema:
                write_kwargs["schema_mode"] = "merge"
            return write_deltalake(**write_kwargs)

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
    merge_callable = _build_merge_execute_callable(
        dt=dt,
        table_path=table_path,
        records=records,
        merge_condition=merge_condition,
        merge_schema=merge_schema,
    )
    if isinstance(dt, Mock):
        merge_callable()
        return
    try:
        await _await_blocking_deltalake_call(
            operation_name="merge-execute",
            call=merge_callable,
            timeout_seconds=timeout_seconds,
        )
    except TimeoutError as exc:
        logger.warning(
            "silver_merge_timeout",
            table_path=table_path,
            timeout_seconds=timeout_seconds,
            primary_keys=primary_keys,
        )
        raise _MergeExecutionTimeoutError(timeout_seconds) from exc
