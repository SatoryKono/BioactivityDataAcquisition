"""Loaded-rows reconciliation orchestration for the Silver FK adapter.

Extracted from the facade so the adapter stays within the Wave 4 and
god-object budgets while delegating branch orchestration here.
"""

from __future__ import annotations

from typing import Any, Protocol, cast

from bioetl.domain.ports import (
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
    apply_reconciliation_mutation,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    build_reconciliation_result,
    complete_dry_run,
    complete_without_mutation,
    partition_source_rows,
    reference_value_set,
)


class ReconcileLoadedRowsHost(Protocol):
    """Adapter surface required to finish loaded-rows reconciliation."""

    def _record_metrics(self, *, scanned: int, retained: int, deleted: int) -> None: ...

    def _log(self, level: str, message: str, **context: object) -> None: ...

    def _write_debug_artifacts(
        self,
        request: ForeignKeyReconciliationRequest,
        result: ForeignKeyReconciliationResult,
        *,
        retained_rows: list[dict[str, object]],
        orphan_rows: list[dict[str, object]],
    ) -> None: ...


async def reconcile_loaded_rows(
    host: ReconcileLoadedRowsHost,
    request: ForeignKeyReconciliationRequest,
    *,
    source_rows: list[dict[str, object]],
    reference_rows: list[dict[str, object]],
) -> ForeignKeyReconciliationResult:
    """Reconcile in-memory source rows against reference values."""
    scanned_rows = len(source_rows)
    reference_values = reference_value_set(request, reference_rows)
    retained_rows, orphan_rows = partition_source_rows(
        request,
        source_rows=source_rows,
        reference_values=reference_values,
    )
    retained_rows_count = len(retained_rows)
    orphan_rows_deleted = len(orphan_rows)
    if request.reference_completeness != "complete":
        return _complete_unproven_reference(
            host,
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows,
            orphan_rows=orphan_rows,
        )
    host._record_metrics(
        scanned=scanned_rows,
        retained=retained_rows_count,
        deleted=orphan_rows_deleted,
    )
    if orphan_rows_deleted == 0:
        return _complete_without_orphans(
            host,
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows,
            orphan_rows=orphan_rows,
        )
    if request.dry_run:
        return _complete_dry_run_outcome(
            host,
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows,
            orphan_rows=orphan_rows,
        )
    return await _complete_with_mutation(
        host,
        request,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows=orphan_rows,
    )


def _complete_unproven_reference(
    host: ReconcileLoadedRowsHost,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: list[dict[str, object]],
    orphan_rows: list[dict[str, object]],
) -> ForeignKeyReconciliationResult:
    """Block mutation when reference completeness is unproven."""
    orphan_rows_deleted = len(orphan_rows)
    host._record_metrics(
        scanned=scanned_rows,
        retained=len(retained_rows) + orphan_rows_deleted,
        deleted=0,
    )
    result = build_reconciliation_result(
        request,
        scanned_rows=scanned_rows,
        retained_rows=len(retained_rows) + orphan_rows_deleted,
        orphan_rows_deleted=0,
        mutated=False,
        would_mutate=False,
        mutation_mode="blocked",
        mutation_blocked_reason="reference_completeness_unproven",
        unproven_unmatched_rows=orphan_rows_deleted,
    )
    host._write_debug_artifacts(
        request,
        result,
        retained_rows=retained_rows + orphan_rows,
        orphan_rows=[],
    )
    return result


def _complete_without_orphans(
    host: ReconcileLoadedRowsHost,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: list[dict[str, object]],
    orphan_rows: list[dict[str, object]],
) -> ForeignKeyReconciliationResult:
    """Finish cleanly when every source row has a reference match."""
    result = complete_without_mutation(
        host,
        request,
        scanned_rows=scanned_rows,
        retained_rows=len(retained_rows),
        orphan_rows_deleted=0,
    )
    host._write_debug_artifacts(
        request,
        result,
        retained_rows=retained_rows,
        orphan_rows=orphan_rows,
    )
    return result


def _complete_dry_run_outcome(
    host: ReconcileLoadedRowsHost,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: list[dict[str, object]],
    orphan_rows: list[dict[str, object]],
) -> ForeignKeyReconciliationResult:
    """Preview orphan deletion without mutating storage."""
    result = complete_dry_run(
        host,
        request,
        scanned_rows=scanned_rows,
        retained_rows=len(retained_rows),
        orphan_rows_deleted=len(orphan_rows),
    )
    host._write_debug_artifacts(
        request,
        result,
        retained_rows=retained_rows,
        orphan_rows=orphan_rows,
    )
    return result


async def _complete_with_mutation(
    host: ReconcileLoadedRowsHost,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: list[dict[str, object]],
    orphan_rows: list[dict[str, object]],
) -> ForeignKeyReconciliationResult:
    """Delete orphan rows and report the destructive outcome."""
    mutation_summary = await apply_reconciliation_mutation(
        cast(Any, host),  # Any: reconciliation mutation helper uses structural host
        request,
        orphan_rows=orphan_rows,
    )
    host._log(
        "info",
        "workflow foreign-key reconciliation completed with mutation",
        source_table=request.source_table,
        reference_table=request.reference_table,
        source_layer=request.source_layer,
        reference_layer=request.reference_layer,
        mutation_layer=request.effective_mutation_layer,
        scanned_rows=scanned_rows,
        retained_rows=len(retained_rows),
        orphan_rows_deleted=len(orphan_rows),
    )
    result = build_reconciliation_result(
        request,
        scanned_rows=scanned_rows,
        retained_rows=len(retained_rows),
        orphan_rows_deleted=len(orphan_rows),
        mutated=True,
        would_mutate=False,
        mutation_mode=cast(
            Any, mutation_summary.mutation_mode
        ),  # Any: external mutation summary compatibility
        quarantine_batch_id=mutation_summary.quarantine_batch_id,
        quarantine_rows_written=mutation_summary.quarantine_rows_written,
        quarantine_error_code=mutation_summary.quarantine_error_code,
    )
    host._write_debug_artifacts(
        request,
        result,
        retained_rows=retained_rows,
        orphan_rows=orphan_rows,
    )
    return result
