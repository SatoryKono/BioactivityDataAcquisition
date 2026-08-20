"""Support helpers for workflow foreign-key reconciliation."""

from __future__ import annotations

from collections.abc import Mapping
from math import isnan
from typing import Protocol

from bioetl.domain.ports import (
    ForeignKeyReconciliationMutationMode,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)


class _ReconcileDebugArtifactSink(Protocol):
    def write_reconcile_debug_artifacts(
        self,
        *,
        context: object,
        request: ForeignKeyReconciliationRequest,
        result: ForeignKeyReconciliationResult,
        retained_rows: tuple[Mapping[str, object], ...],
        orphan_rows: tuple[Mapping[str, object], ...],
    ) -> object: ...


NULL_TOKEN = object()

_RUN_IDENTITY_COLUMNS = (
    "_run_id",
    "run_id",
    "composite_run_id",
    "_composite_run_id",
    "workflow_run_id",
)


def filter_source_rows_to_current_run(
    rows: list[dict[str, object]],
    *,
    source_scope: str,
    source_run_ids: tuple[str, ...],
) -> tuple[list[dict[str, object]], str]:
    """Restrict source rows to the current run when CLI --limit scoped delete_orphans.

    Returns (rows, disposition) where disposition is:
    - ``all_current``: no extra filter
    - ``current_run``: filtered to matching run ids
    - ``blocked``: current_run requested but rows cannot be scoped safely
    """
    if source_scope != "current_run":
        return rows, "all_current"
    if not rows:
        return rows, "current_run"
    if not source_run_ids:
        return [], "blocked"
    allowed = {item.strip() for item in source_run_ids if item.strip()}
    column = _first_run_identity_column(rows)
    if column is None:
        return [], "blocked"
    scoped = [row for row in rows if str(row.get(column) or "").strip() in allowed]
    return scoped, "current_run"


def _first_run_identity_column(rows: list[dict[str, object]]) -> str | None:
    """Return the first known run-identity column present in any row."""
    for candidate in _RUN_IDENTITY_COLUMNS:
        if any(candidate in row for row in rows):
            return candidate
    return None


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
    """Partition source rows into retained and orphan rows.

    Rows with any NULL / blank / NaN foreign-key component are always retained.
    SQL-style foreign-key checks do not treat NULL as a missing parent, so
    ``delete_orphans`` must never classify incomplete FK rows as orphans.
    """
    retained_rows: list[dict[str, object]] = []
    orphan_rows: list[dict[str, object]] = []
    source_keys = request.effective_source_keys
    for row in source_rows:
        if row_has_null_foreign_key(row, source_keys):
            retained_rows.append(row)
            continue
        source_key = normalize_row_key(
            row,
            source_keys,
            nulls_equal=request.nulls_equal,
        )
        if source_key is None:
            # Defensive: incomplete keys after null-component check still retain.
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


def row_has_null_foreign_key(
    row: dict[str, object],
    keys: tuple[str, ...],
) -> bool:
    """Return True when any foreign-key component is null, blank, or NaN."""
    return any(normalize_value(row.get(key)) is None for key in keys)


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


def normalize_value(value: object) -> object | None:
    """Normalize one foreign-key value for comparison.

    Invariants:
    - ``None``, blank strings, and NaN are null (``None``).
    - Strings stay distinct from numeric values (``"5"`` != ``5``).
    - Integral numbers that differ only by float form match (``5`` == ``5.0``).
    - Booleans are not collapsed into integers.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, float):
        if isnan(value):
            return None
        if value.is_integer():
            return ("int", int(value))
        return ("float", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return ("str", stripped)
    rendered = str(value).strip()
    if not rendered:
        return None
    return ("other", type(value).__name__, rendered)


__all__ = [
    "build_reconciliation_result",
    "complete_dry_run",
    "complete_without_mutation",
    "emit_reconcile_debug_artifacts",
    "filter_source_rows_to_current_run",
    "log_reconciliation",
    "log_reconciliation_started",
    "normalize_row_key",
    "normalize_value",
    "partition_source_rows",
    "record_reconciliation_metrics",
    "reference_value_set",
    "row_has_null_foreign_key",
]


def record_reconciliation_metrics(
    metrics: object | None,
    *,
    scanned: int,
    retained: int,
    deleted: int,
    scanned_metric: str,
    retained_metric: str,
    deleted_metric: str,
) -> None:
    if metrics is None:
        return
    increment = getattr(metrics, "increment_counter", None)
    if not callable(increment):
        return
    increment(scanned_metric, scanned, {})
    increment(retained_metric, retained, {})
    increment(deleted_metric, deleted, {})


def log_reconciliation(
    logger: object, level: str, message: str, **context: object
) -> None:
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(message, **context)


def log_reconciliation_started(
    adapter: ReconciliationLoggingHost,
    request: ForeignKeyReconciliationRequest,
) -> None:
    """Log the start of one delete_orphans reconciliation pass."""
    adapter._log(
        "info",
        "workflow foreign-key reconciliation started",
        source_table=request.source_table,
        reference_table=request.reference_table,
        source_layer=request.source_layer,
        reference_layer=request.reference_layer,
        mutation_layer=request.effective_mutation_layer,
        source_keys=list(request.effective_source_keys),
        reference_keys=list(request.effective_reference_keys),
        nulls_equal=request.nulls_equal,
    )


def emit_reconcile_debug_artifacts(
    artifact_sink: _ReconcileDebugArtifactSink | None,
    request: ForeignKeyReconciliationRequest,
    result: ForeignKeyReconciliationResult,
    *,
    retained_rows: list[dict[str, object]],
    orphan_rows: list[dict[str, object]],
) -> None:
    if artifact_sink is None:
        return
    if (
        not request.debug_export_enabled
        or request.workflow_run_id is None
        or request.step_id is None
    ):
        return
    artifact_sink.write_reconcile_debug_artifacts(
        context=request,
        request=request,
        result=result,
        retained_rows=tuple(retained_rows),
        orphan_rows=tuple(orphan_rows),
    )
