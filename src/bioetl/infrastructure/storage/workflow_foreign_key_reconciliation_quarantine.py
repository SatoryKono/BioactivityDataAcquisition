# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Mutation and quarantine helpers for workflow FK reconciliation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine_keys import (
    CURRENT_FLAG_COLUMNS,
    VALID_TO_COLUMNS,
    build_orphan_key_rows,
    require_sql_identifier,
    resolve_present_column,
)
import pyarrow as pa
from deltalake.exceptions import DeltaError

from bioetl.domain.ports import (
    ForeignKeyReconciliationRequest,
    LoggerPort,
    QuarantinePort,
    QuarantineWriteRequest,
)
from bioetl.domain.types import BronzeRecord, MetaDict
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow
from bioetl.infrastructure.storage.gold.io_delta_protocols import (
    GoldWriteRetryModuleProtocol,
)
from bioetl.infrastructure.storage.gold.io_delta_runtime import (
    _run_gold_write_with_retry,
)
from bioetl.infrastructure.storage.gold.io_helpers import load_gold_writer_module
from bioetl.infrastructure.storage.silver.operations.delta_operation_protocols import (
    _load_deltalake_module,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_identity import (
    build_quarantine_batch_id,
    coerce_optional_run_id,
    orphan_error_code,
)
from bioetl.infrastructure.time.system_clock import current_utc_time

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY = "foreign_key_reconciliation"
FOREIGN_KEY_ORPHAN_PIPELINE_DEFAULT = "workflow_transforms"


@dataclass(frozen=True, slots=True)
class ReconciliationMutationSummary:
    """Compact mutation/quarantine summary for one FK reconciliation pass."""

    mutation_mode: str
    quarantine_batch_id: str | None = None
    quarantine_rows_written: int = 0
    quarantine_error_code: str | None = None


class ReconciliationMutationHost(Protocol):
    """Adapter surface required by mutation and quarantine helpers."""

    quarantine: QuarantinePort | None
    quarantine_pipeline_name: str | None
    logger: LoggerPort

    @property
    def silver_writer(self) -> SilverWriter: ...

    gold_writer: object | None


async def apply_reconciliation_mutation(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> ReconciliationMutationSummary:
    """Quarantine orphan rows and mutate only the requested storage layer."""
    quarantine_summary = ReconciliationMutationSummary(
        mutation_mode="quarantine_skipped",
        quarantine_error_code=orphan_error_code(request) if orphan_rows else None,
    )
    if orphan_rows:
        quarantine_summary = await quarantine_orphan_rows(
            host,
            request,
            orphan_rows=orphan_rows,
        )

    if request.effective_mutation_layer == "gold":
        await expire_gold_orphan_rows(host, request, orphan_rows=orphan_rows)
        return ReconciliationMutationSummary(
            mutation_mode="gold_scd2_expiry",
            quarantine_batch_id=quarantine_summary.quarantine_batch_id,
            quarantine_rows_written=quarantine_summary.quarantine_rows_written,
            quarantine_error_code=quarantine_summary.quarantine_error_code,
        )

    await delete_silver_orphan_rows(host, request, orphan_rows=orphan_rows)

    return ReconciliationMutationSummary(
        mutation_mode="silver_rewrite",
        quarantine_batch_id=quarantine_summary.quarantine_batch_id,
        quarantine_rows_written=quarantine_summary.quarantine_rows_written,
        quarantine_error_code=quarantine_summary.quarantine_error_code,
    )


async def delete_silver_orphan_rows(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> None:
    """Delete Silver orphan keys in one atomic Delta merge transaction."""
    writer = host.silver_writer
    module = _load_deltalake_module()
    table_path = writer._resolve_table_path(request.source_table)
    primary_keys = tuple(
        require_sql_identifier(key, "primary_keys") for key in request.primary_keys
    )
    key_rows = build_orphan_key_rows(
        orphan_rows,
        primary_keys,
        operation="Silver foreign-key reconciliation cannot delete",
    )
    merge_condition = " AND ".join(
        f"target.{key} = source.{key}" for key in primary_keys
    )
    await asyncio.to_thread(
        _delete_silver_orphan_rows_once,
        module,
        table_path,
        key_rows,
        merge_condition,
    )


def _delete_silver_orphan_rows_once(
    module: Any,  # Any: module providing the DeltaTable runtime seam
    table_path: str,
    key_rows: list[dict[str, object]],
    merge_condition: str,
) -> object:
    """Execute one atomic Silver orphan-key deletion transaction."""
    delta_table = module.DeltaTable(table_path)
    source = pa.Table.from_pylist(key_rows)
    source_reader = pa.RecordBatchReader.from_batches(
        source.schema,
        source.to_batches(),
    )
    return (
        delta_table.merge(
            source=source_reader,
            predicate=merge_condition,
            source_alias="source",
            target_alias="target",
        )
        .when_matched_delete()
        .execute()
    )


async def expire_gold_orphan_rows(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> None:
    """Expire current Gold SCD2 orphan rows without deleting historical records."""
    if not orphan_rows:
        return
    gold_writer = _require_gold_writer(host)
    module = load_gold_writer_module()
    table_path = gold_writer._resolve_table_path(request.source_table)
    table_columns = await _delta_table_column_names(
        module,
        table_path,
        logger=host.logger,
    )

    primary_keys = tuple(
        require_sql_identifier(key, "primary_keys") for key in request.primary_keys
    )
    current_flag_col = require_sql_identifier(
        resolve_present_column(
            orphan_rows,
            CURRENT_FLAG_COLUMNS,
            table_columns=table_columns,
        ),
        "current_flag_column",
    )
    valid_to_col = require_sql_identifier(
        resolve_present_column(
            orphan_rows,
            VALID_TO_COLUMNS,
            table_columns=table_columns,
        ),
        "valid_to_column",
    )
    key_rows = build_orphan_key_rows(
        orphan_rows,
        primary_keys,
        operation="Gold foreign-key reconciliation cannot expire",
    )
    if not key_rows:
        return

    merge_condition = " AND ".join(
        f"target.{key} = source.{key}" for key in primary_keys
    )
    merge_condition += f" AND target.{current_flag_col} = true"
    ts_iso = current_utc_time().isoformat()

    async def _execute_expiry_attempt() -> object:
        return await gold_writer._run_in_executor(
            _expire_gold_orphan_rows_once,
            module,
            table_path,
            key_rows,
            merge_condition,
            valid_to_col,
            current_flag_col,
            ts_iso,
        )

    await _run_gold_write_with_retry(
        cast(GoldWriteRetryModuleProtocol, module),  # pyright: ignore[reportInvalidCast]
        _execute_expiry_attempt,
    )


def _require_gold_writer(
    host: ReconciliationMutationHost,
) -> Any:  # Any: returns gold_writer matching GoldWriteRetryModuleProtocol
    gold_writer = host.gold_writer
    if gold_writer is None:
        raise ValueError(
            "Gold foreign-key reconciliation mutation requires a configured gold_writer"
        )
    for method_name in ("_resolve_table_path", "_run_in_executor"):
        if not callable(getattr(gold_writer, method_name, None)):
            raise ValueError(
                "Configured gold_writer does not expose "
                f"{method_name}() required for SCD2 expiry"
            )
    return gold_writer


def _expire_gold_orphan_rows_once(
    module: Any,  # Any: module matching GoldWriteRetryModuleProtocol
    table_path: str,
    key_rows: list[dict[str, object]],
    merge_condition: str,
    valid_to_col: str,
    current_flag_col: str,
    ts_iso: str,
) -> object:
    """Execute one retryable Gold SCD2 orphan-expiry merge attempt."""
    dt = module.DeltaTable(table_path)
    source = pa.Table.from_pylist(key_rows)
    source_reader = pa.RecordBatchReader.from_batches(
        source.schema, source.to_batches()
    )
    return (
        dt.merge(
            source=source_reader,
            predicate=merge_condition,
            source_alias="source",
            target_alias="target",
        )
        .when_matched_update(
            updates={
                valid_to_col: f"'{ts_iso}'",
                current_flag_col: "false",
            }
        )
        .execute()
    )



async def _delta_table_column_names(
    module: Any,  # Any: gold writer module providing DeltaTable
    table_path: str,
    *,
    logger: LoggerPort,
) -> frozenset[str] | None:
    """Return Gold table column names from Delta schema when available."""

    def _inspect() -> frozenset[str]:
        delta_table = module.DeltaTable(table_path)
        schema = delta_table.schema()
        arrow_schema = delta_schema_to_pyarrow(schema)
        return frozenset(arrow_schema.names)

    try:
        return await asyncio.to_thread(_inspect)
    except (
        AttributeError,
        DeltaError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        pa.ArrowInvalid,
        pa.ArrowTypeError,
    ) as error:
        logger.warning(
            "workflow foreign-key reconciliation schema inspection failed",
            table_path=table_path,
            error_type=type(error).__name__,
            fallback="orphan_rows",
        )
        return None





async def quarantine_orphan_rows(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> ReconciliationMutationSummary:
    """Write orphaned rows to quarantine when the quarantine port is configured."""
    error_code = orphan_error_code(request)
    if host.quarantine is None or not orphan_rows:
        return ReconciliationMutationSummary(
            mutation_mode="quarantine_skipped",
            quarantine_error_code=error_code if orphan_rows else None,
        )

    batch_id = build_quarantine_batch_id(request, orphan_rows=orphan_rows)
    source_table = request.source_table
    reference_table = request.reference_table
    pipeline_name = (
        request.workflow_name
        if request.workflow_name
        else (host.quarantine_pipeline_name or FOREIGN_KEY_ORPHAN_PIPELINE_DEFAULT)
    )
    reason = (
        "Foreign key reconciliation orphan: "
        f"{source_table}.{request.source_key} has no matching row "
        f"in {reference_table}.{request.reference_key}"
    )
    quarantine_rows: list[QuarantineWriteRequest] = []
    for row in orphan_rows:
        quarantine_rows.append(
            {
                "pipeline": pipeline_name,
                "error_code": error_code,
                "payload": cast("BronzeRecord", row),
                "bronze_batch_id": batch_id,
                "run_id": coerce_optional_run_id(request.workflow_run_id),
                "metadata": cast(
                    "MetaDict",
                    {
                        "error_details": {"message": reason},
                        "classification": "filter_rejection",
                        "quarantine_category": FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY,
                        "source_table": source_table,
                        "reference_table": reference_table,
                        "source_layer": request.source_layer,
                        "reference_layer": request.reference_layer,
                        "mutation_layer": request.effective_mutation_layer,
                        "workflow_run_id": request.workflow_run_id,
                        "workflow_name": request.workflow_name,
                        "manifest_id": request.manifest_id,
                        "step_id": request.step_id,
                        "transform_name": request.transform_name,
                    },
                ),
                "ingestion_ts": current_utc_time(),
            }
        )

    await host.quarantine.write_many(quarantine_rows)
    return ReconciliationMutationSummary(
        mutation_mode="quarantine_written",
        quarantine_batch_id=str(batch_id),
        quarantine_rows_written=len(quarantine_rows),
        quarantine_error_code=error_code,
    )


__all__ = [
    "ReconciliationMutationSummary",
    "apply_reconciliation_mutation",
    "quarantine_orphan_rows",
]
