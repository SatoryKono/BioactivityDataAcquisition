"""Infrastructure adapter for workflow foreign-key reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from math import isnan
from uuid import UUID

import pyarrow as pa

from bioetl.domain.context import current_utc_time
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.ports import (
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
)
from bioetl.domain.types import BatchID
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["SilverForeignKeyReconciliationAdapter"]

_NULL_TOKEN = object()
_RECONCILIATION_ROWS_SCANNED_TOTAL = "bioetl_workflow_reconciliation_rows_scanned_total"
_RECONCILIATION_ROWS_RETAINED_TOTAL = (
    "bioetl_workflow_reconciliation_rows_retained_total"
)
_RECONCILIATION_ROWS_DELETED_TOTAL = "bioetl_workflow_reconciliation_rows_deleted_total"
_FOREIGN_KEY_ORPHAN_ERROR_CODE = "FILTERED_OUT_SILVER"
_FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY = "foreign_key_reconciliation"
_FOREIGN_KEY_ORPHAN_PIPELINE_DEFAULT = "workflow_transforms"


def _canonical_reconciliation_value(value: object) -> object:
    if isinstance(value, float) and isnan(value):
        return "NaN"
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_reconciliation_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonical_reconciliation_value(nested) for nested in value]
    return value


def _build_quarantine_batch_id(
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> BatchID:
    return BatchID(
        deterministic_uuid(
            "infrastructure.workflow_foreign_key_reconciliation.quarantine_batch",
            {
                "action": request.action,
                "nulls_equal": request.nulls_equal,
                "orphan_rows": _canonical_reconciliation_value(orphan_rows),
                "reference_keys": list(request.effective_reference_keys),
                "reference_table": request.reference_table,
                "source_keys": list(request.effective_source_keys),
                "source_table": request.source_table,
                "workflow_name": request.workflow_name,
            },
        )
    )


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
            return _build_reconciliation_result(
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
            return _build_reconciliation_result(
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
        reference_values = _reference_value_set(request, reference_rows)
        retained_rows, orphan_rows = _partition_source_rows(
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
            return _complete_without_mutation(
                self,
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=0,
            )

        if request.dry_run:
            return _complete_dry_run(
                self,
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=orphan_rows_deleted,
            )

        await self._apply_reconciliation_mutation(
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
        return _build_reconciliation_result(
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows_count,
            orphan_rows_deleted=orphan_rows_deleted,
            mutated=True,
            would_mutate=False,
        )

    async def _apply_reconciliation_mutation(
        self,
        request: ForeignKeyReconciliationRequest,
        *,
        retained_rows: list[dict[str, object]],
        orphan_rows: list[dict[str, object]],
    ) -> None:
        if orphan_rows:
            await self._quarantine_orphan_rows(request, orphan_rows=orphan_rows)

        self.silver_writer.clear(request.source_table, dry_run=False)
        if not retained_rows:
            return

        source_schema = pa.Table.from_pylist(retained_rows).schema
        await self.silver_writer.write_silver(
            table_name=request.source_table,
            records=retained_rows,
            primary_keys=list(request.primary_keys),
            schema=source_schema,
            mode="merge",
        )

    async def _quarantine_orphan_rows(
        self,
        request: ForeignKeyReconciliationRequest,
        *,
        orphan_rows: list[dict[str, object]],
    ) -> None:
        if self.quarantine is None or not orphan_rows:
            return

        batch_id = _build_quarantine_batch_id(request, orphan_rows=orphan_rows)
        source_table = request.source_table
        reference_table = request.reference_table
        pipeline_name = (
            request.workflow_name
            if request.workflow_name
            else (self.quarantine_pipeline_name or _FOREIGN_KEY_ORPHAN_PIPELINE_DEFAULT)
        )
        reason = (
            "Foreign key reconciliation orphan: "
            f"{source_table}.{request.source_key} has no matching row "
            f"in {reference_table}.{request.reference_key}"
        )
        quarantine_rows: list[dict[str, object]] = []
        for row in orphan_rows:
            metadata = {
                "error_details": {"message": reason},
                "classification": "filter_rejection",
                "quarantine_category": _FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY,
                "source_table": source_table,
                "reference_table": reference_table,
            }
            quarantine_rows.append(
                {
                    "pipeline": pipeline_name,
                    "error_code": _FOREIGN_KEY_ORPHAN_ERROR_CODE,
                    "payload": row,
                    "bronze_batch_id": batch_id,
                    "run_id": None,
                    "metadata": metadata,
                    "ingestion_ts": current_utc_time(),
                }
            )

        await self.quarantine.write_many(quarantine_rows)


def _build_reconciliation_result(
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: int,
    orphan_rows_deleted: int,
    mutated: bool,
    would_mutate: bool,
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
        dry_run=request.dry_run,
        would_mutate=would_mutate,
    )


def _reference_value_set(
    request: ForeignKeyReconciliationRequest,
    reference_rows: list[dict[str, object]],
) -> set[tuple[object, ...]]:
    return {
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


def _partition_source_rows(
    request: ForeignKeyReconciliationRequest,
    *,
    source_rows: list[dict[str, object]],
    reference_values: set[tuple[object, ...]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    retained_rows: list[dict[str, object]] = []
    orphan_rows: list[dict[str, object]] = []
    for row in source_rows:
        source_key = _normalize_row_key(
            row,
            request.effective_source_keys,
            nulls_equal=request.nulls_equal,
        )
        if source_key is not None and source_key in reference_values:
            retained_rows.append(row)
            continue
        orphan_rows.append(row)
    return retained_rows, orphan_rows


def _complete_without_mutation(
    adapter: SilverForeignKeyReconciliationAdapter,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: int,
    orphan_rows_deleted: int,
) -> ForeignKeyReconciliationResult:
    adapter._log(
        "info",
        "workflow foreign-key reconciliation completed without mutation",
        source_table=request.source_table,
        reference_table=request.reference_table,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
    )
    return _build_reconciliation_result(
        request,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
        mutated=False,
        would_mutate=False,
    )


def _complete_dry_run(
    adapter: SilverForeignKeyReconciliationAdapter,
    request: ForeignKeyReconciliationRequest,
    *,
    scanned_rows: int,
    retained_rows: int,
    orphan_rows_deleted: int,
) -> ForeignKeyReconciliationResult:
    adapter._log(
        "info",
        "workflow foreign-key reconciliation skipped quarantine in dry-run preview",
        source_table=request.source_table,
        reference_table=request.reference_table,
        orphan_rows=orphan_rows_deleted,
    )
    adapter._log(
        "warning",
        "workflow foreign-key reconciliation dry-run blocked mutation",
        source_table=request.source_table,
        reference_table=request.reference_table,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
    )
    return _build_reconciliation_result(
        request,
        scanned_rows=scanned_rows,
        retained_rows=retained_rows,
        orphan_rows_deleted=orphan_rows_deleted,
        mutated=False,
        would_mutate=True,
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
