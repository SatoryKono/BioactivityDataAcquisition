"""Infrastructure adapter for workflow foreign-key reconciliation."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

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
    filter_source_rows_to_current_run,
    log_reconciliation_started,
    partition_source_rows,
    reference_value_set,
)

__all__ = [
    "GoldReconciliationReaderProtocol",
    "ReconcileDebugArtifactSinkProtocol",
    "SilverForeignKeyReconciliationAdapter",
    "StorageForeignKeyReconciliationAdapter",
    "filter_current_rows",
]

_RECONCILIATION_ROWS_SCANNED_TOTAL = "bioetl_workflow_reconciliation_rows_scanned_total"
_RECONCILIATION_ROWS_RETAINED_TOTAL = (
    "bioetl_workflow_reconciliation_rows_retained_total"
)
_RECONCILIATION_ROWS_DELETED_TOTAL = "bioetl_workflow_reconciliation_rows_deleted_total"
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
class ReconcileDebugArtifactSinkProtocol(Protocol):
    """Narrow debug-artifact sink used by FK reconciliation export path."""

    def write_reconcile_debug_artifacts(
        self,
        *,
        context: object,
        request: ForeignKeyReconciliationRequest,
        result: ForeignKeyReconciliationResult,
        retained_rows: tuple[Mapping[str, object], ...],
        orphan_rows: tuple[Mapping[str, object], ...],
    ) -> object:
        """Persist row-level debug artifacts for one reconcile result."""
        ...


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
    if isinstance(value, bool):
        return value
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


@dataclass(slots=True)
class SilverForeignKeyReconciliationAdapter(ForeignKeyReconciliationPort):
    silver_writer: SilverWriter
    logger: LoggerPort
    metrics: MetricsPort | None = None
    quarantine: QuarantinePort | None = None
    quarantine_pipeline_name: str | None = None
    gold_writer: GoldReconciliationReaderProtocol | None = None
    artifact_sink: ReconcileDebugArtifactSinkProtocol | None = None

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        if request.action != "delete_orphans":
            raise ValueError(
                "SilverForeignKeyReconciliationAdapter supports only delete_orphans"
            )
        log_reconciliation_started(self, request)

        source_rows = await self._read_source_rows(request)
        if source_rows is None:
            return build_reconciliation_result(
                request,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
                would_mutate=False,
                mutation_mode="missing_source",
            )

        scoped_rows, scope_disposition = filter_source_rows_to_current_run(
            source_rows,
            source_scope=request.source_scope,
            source_run_ids=request.source_run_ids,
        )
        if scope_disposition == "blocked":
            self._log(
                "warning",
                "workflow foreign-key reconciliation current_run scope unbound; "
                "falling back to all current source rows",
                source_table=request.source_table,
                reference_table=request.reference_table,
                source_scope=request.source_scope,
            )
        else:
            source_rows = scoped_rows
        if not source_rows:
            self._record_metrics(scanned=0, retained=0, deleted=0)
            self._log(
                "info",
                "workflow foreign-key reconciliation no-op on empty source",
                source_table=request.source_table,
                reference_table=request.reference_table,
                source_layer=request.source_layer,
                reference_layer=request.reference_layer,
                mutation_layer=request.effective_mutation_layer,
            )
            return build_reconciliation_result(
                request,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
                would_mutate=False,
                mutation_mode="no_op",
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
            return await self._read_rows(
                layer=request.source_layer,
                table_name=request.source_table,
                columns=None,
                current_only=True,
            )
        except FileNotFoundError:
            self._record_metrics(scanned=0, retained=0, deleted=0)
            self._log(
                "warning",
                "workflow foreign-key reconciliation skipped missing source table",
                source_table=request.source_table,
                reference_table=request.reference_table,
                source_layer=request.source_layer,
                reference_layer=request.reference_layer,
                mutation_layer=request.effective_mutation_layer,
            )
            return None

    async def _read_reference_rows(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> list[dict[str, object]]:
        try:
            return await self._read_rows(
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

    async def _read_rows(
        self,
        *,
        layer: str,
        table_name: str,
        columns: list[str] | None,
        current_only: bool,
    ) -> list[dict[str, object]]:
        if layer == "silver":
            rows = await self.silver_writer.read_silver(table_name, columns=columns)
            materialized = [dict(row) for row in rows]
            return filter_current_rows(
                materialized,
                current_only=current_only,
                layer="silver",
            )

        if self.gold_writer is None:
            raise ValueError(
                "Gold foreign-key reconciliation requires a configured gold_writer"
            )
        value = self.gold_writer.read_gold(
            table_name,
            columns=columns,
            current_only=current_only,
        )
        if inspect.isawaitable(value):
            value = await value
        materialized = [
            dict(row) for row in cast(Iterable[Mapping[str, object]], value)
        ]
        # Gold readers apply current_only internally; re-apply as a safety net when
        # payloads still carry SCD flags (sync fakes / partial adapters).
        return filter_current_rows(
            materialized,
            current_only=current_only,
            layer="gold",
        )

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
            result = complete_without_mutation(
                self,
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=0,
            )
            self._write_debug_artifacts(
                request,
                result,
                retained_rows=retained_rows,
                orphan_rows=orphan_rows,
            )
            return result

        if request.dry_run:
            result = complete_dry_run(
                self,
                request,
                scanned_rows=scanned_rows,
                retained_rows=retained_rows_count,
                orphan_rows_deleted=orphan_rows_deleted,
            )
            self._write_debug_artifacts(
                request,
                result,
                retained_rows=retained_rows,
                orphan_rows=orphan_rows,
            )
            return result

        mutation_summary = await apply_reconciliation_mutation(
            cast(Any, self),  # Any: reconciliation mutation helper uses structural host
            request,
            orphan_rows=orphan_rows,
        )
        self._log(
            "info",
            "workflow foreign-key reconciliation completed with mutation",
            source_table=request.source_table,
            reference_table=request.reference_table,
            source_layer=request.source_layer,
            reference_layer=request.reference_layer,
            mutation_layer=request.effective_mutation_layer,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows_count,
            orphan_rows_deleted=orphan_rows_deleted,
        )
        result = build_reconciliation_result(
            request,
            scanned_rows=scanned_rows,
            retained_rows=retained_rows_count,
            orphan_rows_deleted=orphan_rows_deleted,
            mutated=True,
            would_mutate=False,
            mutation_mode=cast(
                Any, mutation_summary.mutation_mode
            ),  # Any: external mutation summary compatibility
            quarantine_batch_id=mutation_summary.quarantine_batch_id,
            quarantine_rows_written=mutation_summary.quarantine_rows_written,
            quarantine_error_code=mutation_summary.quarantine_error_code,
        )
        self._write_debug_artifacts(
            request,
            result,
            retained_rows=retained_rows,
            orphan_rows=orphan_rows,
        )
        return result

    def _write_debug_artifacts(
        self,
        request: ForeignKeyReconciliationRequest,
        result: ForeignKeyReconciliationResult,
        *,
        retained_rows: list[dict[str, object]],
        orphan_rows: list[dict[str, object]],
    ) -> None:
        if self.artifact_sink is None:
            return
        if (
            not request.debug_export_enabled
            or request.workflow_run_id is None
            or request.step_id is None
        ):
            return
        self.artifact_sink.write_reconcile_debug_artifacts(
            context=request,
            request=request,
            result=result,
            retained_rows=tuple(retained_rows),
            orphan_rows=tuple(orphan_rows),
        )


StorageForeignKeyReconciliationAdapter = SilverForeignKeyReconciliationAdapter
