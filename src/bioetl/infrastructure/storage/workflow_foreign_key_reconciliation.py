"""Infrastructure adapter for workflow foreign-key reconciliation."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from bioetl.domain.ports import (
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["SilverForeignKeyReconciliationAdapter"]


@dataclass(slots=True)
class SilverForeignKeyReconciliationAdapter(ForeignKeyReconciliationPort):
    """Reconcile Silver foreign keys through the existing Delta storage seam."""

    silver_writer: SilverWriter

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        if request.action != "delete_orphans":
            raise ValueError(
                "SilverForeignKeyReconciliationAdapter supports only delete_orphans"
            )

        try:
            source_rows = await self.silver_writer.read_silver(request.source_table)
        except FileNotFoundError:
            return ForeignKeyReconciliationResult(
                source_table=request.source_table,
                reference_table=request.reference_table,
                source_key=request.source_key,
                reference_key=request.reference_key,
                action=request.action,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
            )

        reference_rows = await self.silver_writer.read_silver(
            request.reference_table,
            columns=[request.reference_key],
        )
        if not source_rows:
            return ForeignKeyReconciliationResult(
                source_table=request.source_table,
                reference_table=request.reference_table,
                source_key=request.source_key,
                reference_key=request.reference_key,
                action=request.action,
                scanned_rows=0,
                retained_rows=0,
                orphan_rows_deleted=0,
                mutated=False,
            )

        reference_values = {
            str(value)
            for row in reference_rows
            if (value := row.get(request.reference_key)) is not None
            and str(value).strip()
        }
        retained_rows: list[dict[str, object]] = []
        orphan_rows_deleted = 0
        for row in source_rows:
            source_value = row.get(request.source_key)
            if source_value is None or not str(source_value).strip():
                retained_rows.append(row)
                continue
            if str(source_value) in reference_values:
                retained_rows.append(row)
                continue
            orphan_rows_deleted += 1

        if orphan_rows_deleted == 0:
            return ForeignKeyReconciliationResult(
                source_table=request.source_table,
                reference_table=request.reference_table,
                source_key=request.source_key,
                reference_key=request.reference_key,
                action=request.action,
                scanned_rows=len(source_rows),
                retained_rows=len(retained_rows),
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

        return ForeignKeyReconciliationResult(
            source_table=request.source_table,
            reference_table=request.reference_table,
            source_key=request.source_key,
            reference_key=request.reference_key,
            action=request.action,
            scanned_rows=len(source_rows),
            retained_rows=len(retained_rows),
            orphan_rows_deleted=orphan_rows_deleted,
            mutated=True,
        )
