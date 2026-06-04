"""Mutation and quarantine helpers for workflow FK reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from math import isnan
from typing import Protocol
from uuid import UUID

import pyarrow as pa

from bioetl.domain.context import current_utc_time
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.ports import ForeignKeyReconciliationRequest, QuarantinePort
from bioetl.domain.types import BatchID

FOREIGN_KEY_ORPHAN_ERROR_CODE = "FILTERED_OUT_SILVER"
FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY = "foreign_key_reconciliation"
FOREIGN_KEY_ORPHAN_PIPELINE_DEFAULT = "workflow_transforms"


class ReconciliationMutationHost(Protocol):
    """Adapter surface required by mutation and quarantine helpers."""

    quarantine: QuarantinePort | None
    quarantine_pipeline_name: str | None
    silver_writer: object


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
                "reference_table": request.reference_table,
                "source_keys": list(request.effective_source_keys),
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
) -> None:
    """Quarantine orphan rows and rewrite the source table with retained rows."""
    if orphan_rows:
        await quarantine_orphan_rows(host, request, orphan_rows=orphan_rows)

    host.silver_writer.clear(request.source_table, dry_run=False)
    if not retained_rows:
        return

    source_schema = pa.Table.from_pylist(retained_rows).schema
    await host.silver_writer.write_silver(
        table_name=request.source_table,
        records=retained_rows,
        primary_keys=list(request.primary_keys),
        schema=source_schema,
        mode="merge",
    )


async def quarantine_orphan_rows(
    host: ReconciliationMutationHost,
    request: ForeignKeyReconciliationRequest,
    *,
    orphan_rows: list[dict[str, object]],
) -> None:
    """Write orphaned rows to quarantine when the quarantine port is configured."""
    if host.quarantine is None or not orphan_rows:
        return

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
                "error_code": FOREIGN_KEY_ORPHAN_ERROR_CODE,
                "payload": row,
                "bronze_batch_id": batch_id,
                "run_id": None,
                "metadata": {
                    "error_details": {"message": reason},
                    "classification": "filter_rejection",
                    "quarantine_category": FOREIGN_KEY_ORPHAN_QUARANTINE_CATEGORY,
                    "source_table": source_table,
                    "reference_table": reference_table,
                },
                "ingestion_ts": current_utc_time(),
            }
        )

    await host.quarantine.write_many(quarantine_rows)


__all__ = ["apply_reconciliation_mutation"]
