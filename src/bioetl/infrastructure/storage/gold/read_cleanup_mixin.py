# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read/history and cleanup-preview helpers for Gold storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)

_CURRENT_FLAG_COLUMNS = ("_is_current", "is_current")

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.domain.types import GoldRecord


def _build_read_projection(
    *,
    columns: list[str] | None,
    current_only: bool,
) -> list[str] | None:
    """Build a minimal projection for Gold reads when callers request columns.

    When current filtering is requested, read the full row first so tables using
    either ``_is_current`` or ``is_current`` can be filtered before projection.
    """
    if columns is None:
        return None
    if current_only:
        return None

    projection = list(columns)
    return projection


def _current_flag_column(column_names: list[str]) -> str | None:
    """Return the SCD current flag column present in a Gold table."""
    for candidate in _CURRENT_FLAG_COLUMNS:
        if candidate in column_names:
            return candidate
    return None


class GoldWriterReadCleanupMixin:
    """Reusable read/history and cleanup-preview helpers."""

    _resolve_table_path: Callable[[str], str]  # pyright: ignore[reportUninitializedInstanceVariable]
    _run_in_executor: Callable[  # pyright: ignore[reportUninitializedInstanceVariable]
        ..., Awaitable[Any]  # Any: executor returns untyped Delta/Arrow runtime objects
    ]

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[GoldRecord]:
        """Read data from Gold table.

        Returns:
            List of Gold record dicts, filtered to current records if current_only is True.

        Raises:
            FileNotFoundError: If the Gold Delta table does not exist.
        """
        table_path = self._resolve_table_path(table_name)
        module = _load_gold_writer_module()
        projection = _build_read_projection(
            columns=columns,
            current_only=current_only,
        )
        try:
            dt = cast(
                Any,  # Any: DeltaTable runtime type has no complete type stubs
                await self._run_in_executor(lambda: module.DeltaTable(table_path)),
            )
            if projection is None:
                arrow_table = cast(
                    Any,  # Any: pyarrow.Table returned via executor is untyped to mypy
                    await self._run_in_executor(dt.to_pyarrow_table),
                )
            else:
                arrow_table = cast(
                    Any,  # Any: pyarrow.Table returned via executor is untyped to mypy
                    await self._run_in_executor(dt.to_pyarrow_table, projection),
                )
        except DeltaTableNotFoundError as exc:
            raise FileNotFoundError(f"Gold table not found: {table_name}") from exc
        current_flag = (
            _current_flag_column(list(arrow_table.column_names))
            if current_only
            else None
        )
        if current_flag is not None:
            import pyarrow.compute as pc

            arrow_table = arrow_table.filter(pc.equal(arrow_table[current_flag], True))  # pyright: ignore[reportAttributeAccessIssue]
        result: list[GoldRecord] = arrow_table.to_pylist()
        if columns:
            return [{key: record.get(key) for key in columns} for record in result]
        return result

    async def get_history(
        self,
        table_name: str,
        business_key_values: JsonDict | None = None,
        limit: int = 10,
    ) -> list[GoldRecord]:
        """Get history of records in Gold table (for SCD2 tracking).

        Returns:
            List of Gold record dicts sorted by valid_from, truncated to limit.
        """
        table_path = self._resolve_table_path(table_name)
        module = _load_gold_writer_module()
        dt = cast(
            Any,  # Any: DeltaTable runtime type has no complete type stubs
            await self._run_in_executor(lambda: module.DeltaTable(table_path)),
        )
        arrow_table = cast(
            Any,  # Any: pyarrow.Table returned via executor is untyped to mypy
            await self._run_in_executor(dt.to_pyarrow_table),
        )

        if business_key_values:
            import pyarrow.compute as pc

            mask = None
            for key, value in business_key_values.items():
                condition = pc.equal(arrow_table[key], value)  # pyright: ignore[reportAttributeAccessIssue]
                mask = condition if mask is None else pc.and_(mask, condition)  # pyright: ignore[reportAttributeAccessIssue]
            if mask is not None:
                arrow_table = arrow_table.filter(mask)

        if "valid_from" in arrow_table.column_names:
            arrow_table = arrow_table.sort_by([("valid_from", "ascending")])
        result: list[GoldRecord] = arrow_table.to_pylist()
        return result[:limit] if limit > 0 else result

    def preview_cleanup(
        self,
        table_name: str,
    ) -> JsonDict:
        """Preview Gold cleanup scope without deleting files.

        Returns:
            Dictionary with table path, existence flag, file count, layer name, and table name.
        """
        table_path = Path(self._resolve_table_path(table_name))
        exists = table_path.exists()
        file_count = (
            sum(1 for file_path in table_path.rglob("*") if file_path.is_file())
            if exists
            else 0
        )
        return {
            "path": str(table_path),
            "exists": exists,
            "file_count": file_count,
            "layer": "gold",
            "table_name": table_name,
        }


__all__ = ["GoldWriterReadCleanupMixin"]
