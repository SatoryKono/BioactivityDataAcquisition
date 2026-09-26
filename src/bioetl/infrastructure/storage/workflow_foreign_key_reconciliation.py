"""Canonical implementation of workflow foreign-key reconciliation (AUD-005).

This module owns the reconcile algorithm
(``SilverForeignKeyReconciliationAdapter`` /
``StorageForeignKeyReconciliationAdapter``); the sibling
``workflow_foreign_key_reconciliation_{support,quarantine,quarantine_keys,identity}``
modules are its internal implementation detail. The application workflow
transform (``application/workflow/transforms/reconcile_foreign_keys.py``) is a
documented facade that orchestrates this adapter through
``ForeignKeyReconciliationPort`` and must not duplicate storage logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from deltalake.exceptions import DeltaError

from bioetl.domain.ports import (
    ClockPort,
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_loaded import (
    reconcile_loaded_rows,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    GoldReconciliationReaderProtocol,
    GoldSnapshotReaderProtocol,
    read_reference_rows,
    read_source_rows,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    filter_current_rows as filter_current_rows,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    build_reconciliation_result,
    emit_reconcile_debug_artifacts,
    filter_source_rows_to_current_run,
    log_reconciliation,
    log_reconciliation_started,
    record_reconciliation_metrics,
)

__all__ = [
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


@dataclass(slots=True)
class SilverForeignKeyReconciliationAdapter(ForeignKeyReconciliationPort):
    silver_writer: SilverWriter
    logger: LoggerPort
    clock: ClockPort | None = None
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

        source_rows = await read_source_rows(self, request)
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
            raise ValueError(
                "workflow foreign-key reconciliation current_run scope unbound; "
                "mutation blocked"
            )
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

        reference_rows = await read_reference_rows(self, request)
        if (
            request.reference_completeness == "complete"
            and request.reference_identity is not None
            and request.reference_identity != request.reference_table
        ):
            return build_reconciliation_result(
                request,
                scanned_rows=len(source_rows),
                retained_rows=len(source_rows),
                orphan_rows_deleted=0,
                mutated=False,
                would_mutate=False,
                mutation_mode="blocked",
                mutation_blocked_reason="reference_completeness_identity_mismatch",
            )
        result = await self._reconcile_loaded_rows(
            request,
            source_rows=source_rows,
            reference_rows=reference_rows,
        )
        gold_reader: object = self.gold_writer
        if request.source_layer == "gold" and isinstance(
            gold_reader, GoldSnapshotReaderProtocol
        ):
            try:
                snapshot = await gold_reader.read_reconciliation_snapshot(
                    request.source_table
                )
                result = replace(result, source_snapshot=snapshot)
            except (DeltaError, OSError, ValueError, TypeError) as exc:
                self._log(
                    "warning",
                    "Reconciliation snapshot unavailable",
                    error_type=type(exc).__name__,
                )
        return result

    def _record_metrics(self, *, scanned: int, retained: int, deleted: int) -> None:
        record_reconciliation_metrics(
            self.metrics,
            scanned=scanned,
            retained=retained,
            deleted=deleted,
            scanned_metric=_RECONCILIATION_ROWS_SCANNED_TOTAL,
            retained_metric=_RECONCILIATION_ROWS_RETAINED_TOTAL,
            deleted_metric=_RECONCILIATION_ROWS_DELETED_TOTAL,
        )

    def _log(self, level: str, message: str, **context: object) -> None:
        log_reconciliation(self.logger, level, message, **context)

    async def _reconcile_loaded_rows(
        self,
        request: ForeignKeyReconciliationRequest,
        *,
        source_rows: list[dict[str, object]],
        reference_rows: list[dict[str, object]],
    ) -> ForeignKeyReconciliationResult:
        """Delegate loaded-rows orchestration to the extracted module."""
        return await reconcile_loaded_rows(
            self,
            request,
            source_rows=source_rows,
            reference_rows=reference_rows,
        )

    def _write_debug_artifacts(
        self,
        request: ForeignKeyReconciliationRequest,
        result: ForeignKeyReconciliationResult,
        *,
        retained_rows: list[dict[str, object]],
        orphan_rows: list[dict[str, object]],
    ) -> None:
        emit_reconcile_debug_artifacts(
            self.artifact_sink,
            request,
            result,
            retained_rows=retained_rows,
            orphan_rows=orphan_rows,
        )


StorageForeignKeyReconciliationAdapter = SilverForeignKeyReconciliationAdapter
