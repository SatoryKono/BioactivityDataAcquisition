"""Support helpers for workflow foreign-key reconciliation."""

from __future__ import annotations

from math import isnan
from typing import Protocol

from bioetl.domain.ports import (
    ForeignKeyReconciliationMutationMode,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)

NULL_TOKEN = object()


class ReconciliationLoggingHost(Protocol):
    """Adapter logging surface required by completion helpers."""

    def _log(self, level: str, message: str, **context: object) -> None: ...


def build_reconciliation_result(
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: int,
    orphan_rows_deleted: int,
    mutated: bool,
    would_mutate: bool,
    mutation_mode: ForeignKeyReconciliationMutationMode = "unknown",
    quarantine_batch_id: str | None = None,
    quarantine_rows_written: int = 0,
    quarantine_error_code: str | None = None,
) -> ForeignKeyReconciliationResult:
    """Build the public reconciliation result payload."""
    return ForeignKeyReconciliationResult(
        source_table=request.source_table,
        reference_table=request.reference_table,
        source_key=request.source_key,
        reference_key=request.reference_key,
        action=request.action,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
        mutated=mutated,
        source_layer=request.source_layer,
        reference_layer=request.reference_layer,
        mutation_layer=request.effective_mutation_layer,
        dry_run=request.dry_run,
        would_mutate=would_mutate,
        mutation_mode=mutation_mode,
        quarantine_batch_id=quarantine_batch_id,
        quarantine_rows_written=quarantine_rows_written,
        quarantine_error_code=quarantine_error_code,
    )


def reference_value_set(
    request: ForeignKeyReconciliationRequest,
    reference_rows: list[dict[str, object]],
) -> set[tuple[object, ...]]:
    """Return normalized reference key values present in the reference table."""
    return {
        key
        for row in reference_rows
        if (
            key := normalize_row_key(
                row,
                request.effective_reference_keys,
                nulls_equal=request.nulls_equal,
            )
        )
        is not None
    }


def partition_source_rows(
    request: ForeignKeyReconciliationRequest,
    *,
    source_rows: list[dict[str, object]],
    reference_values: set[tuple[object, ...]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Partition source rows into retained and orphan rows."""
    retained_rows: list[dict[str, object]] = []
    orphan_rows: list[dict[str, object]] = []
    for row in source_rows:
        source_key = normalize_row_key(
            row,
            request.effective_source_keys,
            nulls_equal=request.nulls_equal,
        )
        if source_key is None:
            # nulls_equal=False and incomplete FK: SQL-like NULL does not fail the
            # foreign-key check, so retain the row instead of treating it as orphan.
            retained_rows.append(row)
            continue
        if source_key in reference_values:
            retained_rows.append(row)
            continue
        orphan_rows.append(row)
    return retained_rows, orphan_rows


def complete_without_mutation(
    host: ReconciliationLoggingHost,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: int,
    orphan_rows_deleted: int,
) -> ForeignKeyReconciliationResult:
    """Complete a reconciliation pass that found no mutation work."""
    host._log(
        "info",
        "workflow foreign-key reconciliation completed without mutation",
        source_table=request.source_table,
        reference_table=request.reference_table,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
    )
    return build_reconciliation_result(
        request,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
        mutated=False,
        would_mutate=False,
        mutation_mode="no_op",
    )


def complete_dry_run(
    host: ReconciliationLoggingHost,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: int,
    orphan_rows_deleted: int,
) -> ForeignKeyReconciliationResult:
    """Complete a dry-run reconciliation pass without mutating storage."""
    host._log(
        "info",
        "workflow foreign-key reconciliation skipped quarantine in dry-run preview",
        source_table=request.source_table,
        reference_table=request.reference_table,
        orphan_rows=orphan_rows_deleted,
    )
    host._log(
        "warning",
        "workflow foreign-key reconciliation dry-run blocked mutation",
        source_table=request.source_table,
        reference_table=request.reference_table,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
    )
    return build_reconciliation_result(
        request,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
        mutated=False,
        would_mutate=True,
        mutation_mode="dry_run_preview",
        quarantine_error_code=(
            "FILTERED_OUT_GOLD"
            if request.effective_mutation_layer == "gold"
            else "FILTERED_OUT_SILVER"
        ),
    )


def normalize_row_key(
    row: dict[str, object],
    keys: tuple[str, ...],
    *,
    nulls_equal: bool,
) -> tuple[object, ...] | None:
    """Normalize a row key for foreign-key comparison."""
    normalized: list[object] = []
    for key in keys:
        value = row.get(key)
        normalized_value = normalize_value(value)
        if normalized_value is None:
            if nulls_equal:
                normalized.append(NULL_TOKEN)
                continue
            return None
        normalized.append(normalized_value)
    return tuple(normalized)


def normalize_value(value: object) -> str | None:
    """Normalize one foreign-key value for comparison."""
    if value is None:
        return None
    if isinstance(value, float) and isnan(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return stripped
    rendered = str(value).strip()
    if not rendered:
        return None
    return rendered


__all__ = [
    "build_reconciliation_result",
    "complete_dry_run",
    "complete_without_mutation",
    "partition_source_rows",
    "reference_value_set",
]
