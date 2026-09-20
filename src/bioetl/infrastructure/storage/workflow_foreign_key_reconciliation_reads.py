"""Row-reading support for workflow foreign-key reconciliation (AUD-005)."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Iterable, Mapping, Sequence
from typing import Protocol, cast, runtime_checkable

from bioetl.domain.ports import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = [
    "ForeignKeyReadsHost",
    "GoldReconciliationReaderProtocol",
    "GoldSnapshotReaderProtocol",
    "filter_current_rows",
    "read_reference_rows",
    "read_rows",
    "read_source_rows",
]


_CURRENT_FLAG_COLUMNS = ("_is_current", "is_current")


class ForeignKeyReadsHost(Protocol):
    """Adapter read surface required by row-reading helpers."""

    silver_writer: SilverWriter
    gold_writer: GoldReconciliationReaderProtocol | None

    def _record_metrics(self, *, scanned: int, retained: int, deleted: int) -> None: ...

    def _log(self, level: str, message: str, **context: object) -> None: ...


_CURRENT_FLAG_COLUMNS = ("_is_current", "is_current")


@runtime_checkable
class GoldReconciliationReaderProtocol(Protocol):
    """Narrow gold reader seam required by foreign-key reconciliation.

    Implementations may expose a sync or async ``read_gold``; the adapter
    awaits awaitable results.
    """

    def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> Sequence[Mapping[str, object]] | Awaitable[Sequence[Mapping[str, object]]]:
        """Read Gold rows, optionally restricted to current SCD2 versions."""
        ...


@runtime_checkable
class GoldSnapshotReaderProtocol(Protocol):
    async def read_reconciliation_snapshot(self, table_name: str) -> dict[str, int]: ...


def _current_flag_column(rows: Sequence[Mapping[str, object]]) -> str | None:
    """Return the SCD current-flag column present in row payloads."""
    if not rows:
        return None
    for candidate in _CURRENT_FLAG_COLUMNS:
        if any(candidate in row for row in rows):
            return candidate
    return None


def _is_current_flag_value(value: object) -> bool:
    """Return True for truthy SCD current flags (bool True / 1 / 'true')."""
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "t", "yes"}
    return False


def filter_current_rows(
    rows: list[dict[str, object]],
    *,
    current_only: bool,
    layer: str,
) -> list[dict[str, object]]:
    """Filter rows to current SCD versions when a current-flag column is present.

    Silver is normally a current-state medallion layer without SCD2 flags. When
    ``current_only`` is requested and no flag column exists, all rows are
    retained (they are already current-state). When a flag column exists, only
    rows with a true current flag are retained so Silver cannot silently ignore
    the flag when present.
    """
    del layer  # layer reserved for future layer-specific policies
    if not current_only or not rows:
        return rows
    flag_column = _current_flag_column(rows)
    if flag_column is None:
        return rows
    return [row for row in rows if _is_current_flag_value(row.get(flag_column))]


async def read_source_rows(
    host: ForeignKeyReadsHost,
    request: ForeignKeyReconciliationRequest,
) -> list[dict[str, object]] | None:
    try:
        return await read_rows(
            host,
            layer=request.source_layer,
            table_name=request.source_table,
            columns=None,
            current_only=True,
        )
    except FileNotFoundError:
        host._record_metrics(scanned=0, retained=0, deleted=0)
        host._log(
            "warning",
            "workflow foreign-key reconciliation skipped missing source table",
            source_table=request.source_table,
            reference_table=request.reference_table,
            source_layer=request.source_layer,
            reference_layer=request.reference_layer,
            mutation_layer=request.effective_mutation_layer,
        )
        return None


async def read_reference_rows(
    host: ForeignKeyReadsHost,
    request: ForeignKeyReconciliationRequest,
) -> list[dict[str, object]]:
    try:
        return await read_rows(
            host,
            layer=request.reference_layer,
            table_name=request.reference_table,
            columns=list(request.effective_reference_keys),
            current_only=True,
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "foreign-key reconciliation reference table not found: "
            f"{request.reference_table} ({request.reference_layer})"
        ) from exc


async def read_rows(
    host: ForeignKeyReadsHost,
    *,
    layer: str,
    table_name: str,
    columns: list[str] | None,
    current_only: bool,
) -> list[dict[str, object]]:
    if layer == "silver":
        rows = await host.silver_writer.read_silver(table_name, columns=columns)
        materialized = [dict(row) for row in rows]
        return filter_current_rows(
            materialized,
            current_only=current_only,
            layer="silver",
        )

    if host.gold_writer is None:
        raise ValueError(
            "Gold foreign-key reconciliation requires a configured gold_writer"
        )
    value = host.gold_writer.read_gold(
        table_name,
        columns=columns,
        current_only=current_only,
    )
    if inspect.isawaitable(value):
        value = await value
    materialized = [dict(row) for row in cast(Iterable[Mapping[str, object]], value)]
    # Gold readers apply current_only internally; re-apply as a safety net when
    # payloads still carry SCD flags (sync fakes / partial adapters).
    return filter_current_rows(
        materialized,
        current_only=current_only,
        layer="gold",
    )
