"""Pure row-set helpers for deterministic workflow row reconciliation."""

from __future__ import annotations

from math import isnan
from typing import Final

from bioetl.domain.ports import (
    RowReconciliationConfig,
    RowReconciliationLayer,
    RowReconciliationMissingColumnError,
    RowReconciliationResult,
    RowReconciliationTypePolicyError,
)

NULL_TOKEN: Final = object()


def reconcile_loaded_rows(
    config: RowReconciliationConfig,
    *,
    left_rows: list[dict[str, object]],
    right_rows: list[dict[str, object]],
    implementation: str,
) -> RowReconciliationResult:
    """Reconcile already-loaded left/right rows with left-semi semantics."""
    _validate_key_columns(left_rows, config.left_columns, side="left")
    _validate_key_columns(right_rows, config.right_columns, side="right")
    _validate_strict_key_types(config, left_rows=left_rows, right_rows=right_rows)

    right_keys, null_key_rows_right = _right_key_set(
        right_rows,
        config.right_columns,
        nulls_equal=config.nulls_equal,
    )
    kept_rows, null_key_rows_left = _kept_left_rows(
        left_rows,
        config.left_columns,
        right_keys=right_keys,
        nulls_equal=config.nulls_equal,
    )
    return RowReconciliationResult(
        layer=RowReconciliationLayer(config.layer),
        left_table=config.left_table,
        right_table=config.right_table,
        left_columns=config.left_columns,
        right_columns=config.right_columns,
        left_primary_keys=config.left_primary_keys,
        input_left_rows=len(left_rows),
        input_right_rows=len(right_rows),
        kept_rows=len(kept_rows),
        excluded_rows=len(left_rows) - len(kept_rows),
        null_key_rows_left=null_key_rows_left,
        null_key_rows_right=null_key_rows_right,
        distinct_right_keys=len(right_keys),
        rows=tuple(kept_rows),
        implementation=implementation,
        nulls_equal=config.nulls_equal,
        type_policy=config.type_policy,
        preserve_order=config.preserve_order,
        report_only=config.report_only,
        mutated=False,
    )


def _validate_key_columns(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
    *,
    side: str,
) -> None:
    missing: set[str] = set()
    for row in rows:
        for column in columns:
            if column not in row:
                missing.add(column)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise RowReconciliationMissingColumnError(
            f"reconcile_rows missing {side} key columns: {missing_columns}"
        )


def _validate_strict_key_types(
    config: RowReconciliationConfig,
    *,
    left_rows: list[dict[str, object]],
    right_rows: list[dict[str, object]],
) -> None:
    if config.type_policy.value != "strict":
        raise RowReconciliationTypePolicyError(
            f"Unsupported reconcile_rows type_policy={config.type_policy.value!r}"
        )
    left_types = _column_types(left_rows, config.left_columns)
    right_types = _column_types(right_rows, config.right_columns)
    for index, (left_column, right_column) in enumerate(
        zip(config.left_columns, config.right_columns, strict=True)
    ):
        observed_types = left_types[index] | right_types[index]
        if len(observed_types) <= 1:
            continue
        observed = ", ".join(sorted(type_.__name__ for type_ in observed_types))
        raise RowReconciliationTypePolicyError(
            "reconcile_rows strict type_policy requires matching non-null "
            f"types for left.{left_column} and right.{right_column}; got {observed}"
        )


def _column_types(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
) -> tuple[frozenset[type[object]], ...]:
    return tuple(
        frozenset(
            type(row[column])
            for row in rows
            if column in row and not _is_null(row[column])
        )
        for column in columns
    )


def _right_key_set(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
    *,
    nulls_equal: bool,
) -> tuple[set[tuple[object, ...]], int]:
    right_keys: set[tuple[object, ...]] = set()
    null_key_rows = 0
    for row in rows:
        row_key, has_null = _row_key(row, columns, nulls_equal=nulls_equal)
        if has_null:
            null_key_rows += 1
        if row_key is not None:
            right_keys.add(row_key)
    return right_keys, null_key_rows


def _kept_left_rows(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
    *,
    right_keys: set[tuple[object, ...]],
    nulls_equal: bool,
) -> tuple[list[dict[str, object]], int]:
    kept_rows: list[dict[str, object]] = []
    null_key_rows = 0
    for row in rows:
        row_key, has_null = _row_key(row, columns, nulls_equal=nulls_equal)
        if has_null:
            null_key_rows += 1
        if row_key is not None and row_key in right_keys:
            kept_rows.append(dict(row))
    return kept_rows, null_key_rows


def _row_key(
    row: dict[str, object],
    columns: tuple[str, ...],
    *,
    nulls_equal: bool,
) -> tuple[tuple[object, ...] | None, bool]:
    key: list[object] = []
    has_null = False
    for column in columns:
        value = row[column]
        if _is_null(value):
            has_null = True
            if not nulls_equal:
                return None, has_null
            key.append(NULL_TOKEN)
            continue
        key.append(value)
    return tuple(key), has_null


def _is_null(value: object) -> bool:
    return value is None or (isinstance(value, float) and isnan(value))


__all__ = ["reconcile_loaded_rows"]
