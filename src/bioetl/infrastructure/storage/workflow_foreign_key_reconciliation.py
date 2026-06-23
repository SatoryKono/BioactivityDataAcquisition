"""Infrastructure adapter for workflow foreign-key reconciliation."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.ports import (
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
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

__all__ = ["SilverForeignKeyReconciliationAdapter"]

_RECONCILIATION_ROWS_SCANNED_TOTAL = "bioetl_workflow_reconciliation_rows_scanned_total"
_RECONCILIATION_ROWS_RETAINED_TOTAL = (
    "bioetl_workflow_reconciliation_rows_retained_total"
)
_RECONCILIATION_ROWS_DELETED_TOTAL = "bioetl_workflow_reconciliation_rows_deleted_total"


@dataclass(slots=True)
class SilverForeignKeyReconciliationAdapter(ForeignKeyReconciliationPort):
    """Reconcile Silver foreign keys through the existing Delta storage seam."""

    silver_writer: SilverWriter
    logger: LoggerPort
    metrics: MetricsPort | None = None
    quarantine: QuarantinePort | None = None
    quarantine_pipeline_name: str | None = None

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        if request.action != "delete_orphans":
            raise ValueError(
                "SilverForeignKeyReconciliationAdapter supports only delete_orphans"
            )

        self._log(
            "info",
            "workflow foreign-key reconciliation started",
            source_table=request.source_table,
            reference_table=request.reference_table,
            source_keys=list(request.effective_source_keys),
            reference_keys=list(request.effective_reference_keys),
            nulls_equal=request.nulls_equal,
        )

        source_rows = await self._read_source_rows(request)
        if source_rows is None:
            return build_reconciliation_result(
                request,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
                would_mutate=False,
            )

        if not source_rows:
            self._record_metrics(scanned=0, retained=0, deleted=0)
            self._log(
                "info",
                "workflow foreign-key reconciliation no-op on empty source",
                source_table=request.source_table,
                reference_table=request.reference_table,
            )
            return build_reconciliation_result(
                request,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
                would_mutate=False,
            )

        reference_rows = await self._read_reference_rows(request)
        return await self._reconcile_loaded_rows(
            request,
            source_rows=source_rows,
            reference_rows=reference_rows,
        )

    def _record_metrics(self, *, scanned: int, retained: int, deleted: int) -> None:
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_SCANNED_TOTAL,
            scanned,
            {},
        )
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_RETAINED_TOTAL,
            retained,
            {},
        )
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_DELETED_TOTAL,
            deleted,
            {},
        )

    def _log(self, level: str, message: str, **context: object) -> None:
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message, **context)

    async def _read_source_rows(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> list[dict[str, object]] | None:
        try:
            return await self.silver_writer.read_silver(request.source_table)
        except FileNotFoundError:
            self._record_metrics(scanned=0, retained=0, deleted=0)
            self._log(
                "warning",
                "workflow foreign-key reconciliation skipped missing source table",
                source_table=request.source_table,
                reference_table=request.reference_table,
            )
            return None

    async def _read_reference_rows(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> list[dict[str, object]]:
        try:
            return await self.silver_writer.read_silver(
                request.reference_table,
                columns=list(request.effective_reference_keys),
            )
        except FileNotFoundError:
            return []

    async def _reconcile_loaded_rows(
        self,
        request: ForeignKeyReconciliationRequest,
        *,
        source_rows: list[dict[str, object]],
        reference_rows: list[dict[str, object]],
    ) -> ForeignKeyReconciliationResult:
        scanned_rows = len(source_rows)
        reference_values = reference_value_set(request, reference_rows)
        retained_rows, orphan_rows = partition_source_rows(
            request,
            source_rows=source_rows,
            reference_values=reference_values,
        )
        retained_rows_count = len(retained_rows)
        orphan_rows_deleted = len(orphan_rows)
        self._record_metrics(
            scanned=scanned_rows,
            retained=retained_rows_count,
            deleted=orphan_rows_deleted,
        )

        if orphan_rows_deleted == 0:
            return complete_without_mutation(
                self,
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=0,
            )

        if request.dry_run:
            return complete_dry_run(
                self,
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=orphan_rows_deleted,
            )

        await apply_reconciliation_mutation(
            self,
            request,
            retained_rows=retained_rows,
            orphan_rows=orphan_rows,
        )
        self._log(
            "info",
            "workflow foreign-key reconciliation completed with mutation",
            source_table=request.source_table,
            reference_table=request.reference_table,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows_count,
            orphan_rows_deleted=orphan_rows_deleted,
        )
        return build_reconciliation_result(
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows_count,
            orphan_rows_deleted=orphan_rows_deleted,
            mutated=True,
            would_mutate=False,
        )
