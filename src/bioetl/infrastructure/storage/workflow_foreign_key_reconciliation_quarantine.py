"""Mutation and quarantine helpers for workflow FK reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from math import isnan
from typing import Any, Protocol, cast
from uuid import UUID

import pyarrow as pa

from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.ports import ForeignKeyReconciliationRequest, QuarantinePort
from bioetl.domain.types import BatchID
from bioetl.infrastructure.storage.gold.io_delta_protocols import (
    GoldWriteRetryModuleProtocol,
)
from bioetl.infrastructure.storage.gold.io_delta_runtime import (
    _run_gold_write_with_retry,
)
from bioetl.infrastructure.storage.gold.io_helpers import load_gold_writer_module
from bioetl.infrastructure.time.system_clock import current_utc_time

FOREIGN_KEY_ORPHAN_ERROR_CODE = "FILTERED_OUT_SILVER"
FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE = "FILTERED_OUT_GOLD"
FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY = "foreign_key_reconciliation"
FOREIGN_KEY_ORPHAN_PIPELINE_DEFAULT = "workflow_transforms"
_CURRENT_FLAG_COLUMNS = ("_is_current", "is_current")
_VALID_TO_COLUMNS = ("_valid_to", "valid_to")


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
    silver_writer: object
    gold_writer: object | None


def canonical_reconciliation_value(value: object) -> object:
    """Return deterministic JSON-compatible value used in quarantine batch IDs."""
    if isinstance(value, float) and isnan(value):
        return "NaN"
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): canonical_reconciliation_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [canonical_reconciliation_value(nested) for nested in value]
    return value


def build_quarantine_batch_id(
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> BatchID:
    """Build deterministic quarantine batch identity for orphan rows."""
    return BatchID(
        deterministic_uuid(
            "infrastructure.workflow_foreign_key_reconciliation.quarantine_batch",
            {
                "action": request.action,
                "nulls_equal": request.nulls_equal,
                "orphan_rows": canonical_reconciliation_value(orphan_rows),
                "reference_keys": list(request.effective_reference_keys),
                "reference_layer": request.reference_layer,
                "reference_table": request.reference_table,
                "mutation_layer": request.effective_mutation_layer,
                "source_keys": list(request.effective_source_keys),
                "source_layer": request.source_layer,
                "source_table": request.source_table,
                "workflow_name": request.workflow_name,
            },
        )
    )


async def apply_reconciliation_mutation(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    retained_rows: list[dict[str, object]],
    orphan_rows: list[dict[str, object]],
) -> ReconciliationMutationSummary:
    """Quarantine orphan rows and mutate only the requested storage layer."""
    quarantine_summary = ReconciliationMutationSummary(
        mutation_mode="quarantine_skipped",
        quarantine_error_code=_orphan_error_code(request) if orphan_rows else None,
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

    host.silver_writer.clear(request.source_table, dry_run=False)
    if retained_rows:
        source_schema = pa.Table.from_pylist(retained_rows).schema
        await host.silver_writer.write_silver(
            table_name=request.source_table,
            records=retained_rows,
            primary_keys=list(request.primary_keys),
            schema=source_schema,
            mode="merge",
        )

    return ReconciliationMutationSummary(
        mutation_mode="silver_rewrite",
        quarantine_batch_id=quarantine_summary.quarantine_batch_id,
        quarantine_rows_written=quarantine_summary.quarantine_rows_written,
        quarantine_error_code=quarantine_summary.quarantine_error_code,
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
    current_flag_col = _resolve_present_column(orphan_rows, _CURRENT_FLAG_COLUMNS)
    valid_to_col = _resolve_present_column(orphan_rows, _VALID_TO_COLUMNS)
    key_rows = _build_gold_orphan_key_rows(orphan_rows, request.primary_keys)
    if not key_rows:
        return

    module = load_gold_writer_module()
    table_path = gold_writer._resolve_table_path(request.source_table)
    merge_condition = " AND ".join(
        f"target.{key} = source.{key}" for key in request.primary_keys
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
        cast(GoldWriteRetryModuleProtocol, module),
        _execute_expiry_attempt,
    )


def _require_gold_writer(host: ReconciliationMutationHost) -> Any:
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
    module: Any,
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


def _resolve_present_column(
    rows: list[dict[str, object]],
    candidates: tuple[str, ...],
) -> str:
    for candidate in candidates:
        if any(candidate in row for row in rows):
            return candidate
    raise ValueError(
        "Gold foreign-key reconciliation requires SCD2 metadata column "
        f"from {candidates}"
    )


def _build_gold_orphan_key_rows(
    orphan_rows: list[dict[str, object]],
    primary_keys: tuple[str, ...],
) -> list[dict[str, object]]:
    key_rows: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for row in orphan_rows:
        key_values: list[object] = []
        for primary_key in primary_keys:
            if primary_key not in row or row[primary_key] is None:
                raise ValueError(
                    "Gold foreign-key reconciliation cannot expire orphan row "
                    f"without non-null primary key {primary_key}"
                )
            key_values.append(row[primary_key])
        key_tuple = tuple(key_values)
        if key_tuple in seen:
            continue
        seen.add(key_tuple)
        key_rows.append(dict(zip(primary_keys, key_values, strict=True)))
    return key_rows


async def quarantine_orphan_rows(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> ReconciliationMutationSummary:
    """Write orphaned rows to quarantine when the quarantine port is configured."""
    error_code = _orphan_error_code(request)
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
    quarantine_rows: list[dict[str, object]] = []
    for row in orphan_rows:
        quarantine_rows.append(
            {
                "pipeline": pipeline_name,
                "error_code": error_code,
                "payload": row,
                "bronze_batch_id": batch_id,
                "run_id": None,
                "metadata": {
                    "error_details": {"message": reason},
                    "classification": "filter_rejection",
                    "quarantine_category": FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY,
                    "source_table": source_table,
                    "reference_table": reference_table,
                    "source_layer": request.source_layer,
                    "reference_layer": request.reference_layer,
                    "mutation_layer": request.effective_mutation_layer,
                },
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


def _orphan_error_code(request: ForeignKeyReconciliationRequest) -> str:
    if request.effective_mutation_layer == "gold":
        return FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE
    return FOREIGN_KEY_ORPHAN_ERROR_CODE


__all__ = ["ReconciliationMutationSummary", "apply_reconciliation_mutation"]
