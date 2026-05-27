"""Infrastructure adapter for workflow foreign-key reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan

import pyarrow as pa

from bioetl.domain.ports import (
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
    LoggerPort,
    MetricsPort,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["SilverForeignKeyReconciliationAdapter"]

_NULL_TOKEN = object()
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
            return self._build_reconciliation_result(
                request,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
            )

        if not source_rows:
            self._record_metrics(scanned=0, retained=0, deleted=0)
            self._log(
                "info",
                "workflow foreign-key reconciliation no-op on empty source",
                source_table=request.source_table,
                reference_table=request.reference_table,
            )
            return self._build_reconciliation_result(
                request,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
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
        reference_values = {
            key
            for row in reference_rows
            if (
                key := _normalize_row_key(
                    row,
                    request.effective_reference_keys,
                    nulls_equal=request.nulls_equal,
                )
            )
            is not None
        }
        retained_rows: list[dict[str, object]] = []
        orphan_rows_deleted = 0
        for row in source_rows:
            source_key = _normalize_row_key(
                row,
                request.effective_source_keys,
                nulls_equal=request.nulls_equal,
            )
            if source_key is not None and source_key in reference_values:
                retained_rows.append(row)
                continue
            orphan_rows_deleted += 1

        scanned_rows = len(source_rows)
        retained_rows_count = len(retained_rows)
        self._record_metrics(
            scanned=scanned_rows,
            retained=retained_rows_count,
            deleted=orphan_rows_deleted,
        )

        if orphan_rows_deleted == 0:
            self._log(
                "info",
                "workflow foreign-key reconciliation completed without mutation",
                source_table=request.source_table,
                reference_table=request.reference_table,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=orphan_rows_deleted,
            )
            return self._build_reconciliation_result(
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=0,
                mutated=False,
            )

        self.silver_writer.clear(request.source_table, dry_run=False)
        if retained_rows:
            source_schema = pa.Table.from_pylist(retained_rows).schema
            await self.silver_writer.write_silver(
                table_name=request.source_table,
                records=retained_rows,
                primary_keys=list(request.primary_keys),
                schema=source_schema,
                mode="merge",
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
        return self._build_reconciliation_result(
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows_count,
            orphan_rows_deleted=orphan_rows_deleted,
            mutated=True,
        )

    def _build_reconciliation_result(
        self,
        request: ForeignKeyReconciliationRequest,
        *,
        scanned_rows: int,
        retained_rows: int,
        orphan_rows_deleted: int,
        mutated: bool,
    ) -> ForeignKeyReconciliationResult:
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
        )


def _normalize_row_key(
    row: dict[str, object],
    keys: tuple[str, ...],
    *,
    nulls_equal: bool,
) -> tuple[object, ...] | None:
    normalized: list[object] = []
    for key in keys:
        value = row.get(key)
        normalized_value = _normalize_value(value)
        if normalized_value is None:
            if nulls_equal:
                normalized.append(_NULL_TOKEN)
                continue
            return None
        normalized.append(normalized_value)
    return tuple(normalized)


def _normalize_value(value: object) -> str | None:
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
