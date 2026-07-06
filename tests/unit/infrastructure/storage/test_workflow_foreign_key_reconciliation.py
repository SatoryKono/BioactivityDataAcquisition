"""Unit tests for workflow foreign-key reconciliation storage adapter."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)

pytestmark = pytest.mark.unit


@dataclass
class _GoldReader:
    rows_by_table: dict[str, list[dict[str, object]]]

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, object]]:
        del current_only
        if table_name not in self.rows_by_table:
            raise FileNotFoundError(table_name)
        rows = self.rows_by_table[table_name]
        if columns is None:
            return [dict(row) for row in rows]
        return [
            {column: row[column] for column in columns if column in row}
            for row in rows
        ]


@dataclass
class _SilverWriter:
    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, object]]:
        del table_name, columns
        raise AssertionError("Silver should not be read for Gold reconciliation")


@dataclass
class _Logger:
    events: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)

    def info(self, message: str, **context: object) -> None:
        self.events.append(("info", message, dict(context)))

    def warning(self, message: str, **context: object) -> None:
        self.events.append(("warning", message, dict(context)))


@dataclass
class _Quarantine:
    writes: list[dict[str, object]] = field(default_factory=list)

    async def write_many(self, records: list[dict[str, object]]) -> None:
        self.writes.extend(records)


@pytest.mark.asyncio
async def test_gold_dry_run_does_not_mutate_or_quarantine() -> None:
    quarantine = _Quarantine()
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverWriter(),  # type: ignore[arg-type]
        gold_writer=_GoldReader(
            {
                "chembl.assay": [
                    {
                        "assay_id": "CHEMBL_A1",
                        "target_id": "CHEMBL_T999",
                        "_is_current": True,
                    }
                ],
                "chembl.target": [],
            }
        ),
        logger=_Logger(),  # type: ignore[arg-type]
        quarantine=quarantine,  # type: ignore[arg-type]
    )

    result = await adapter.reconcile_foreign_keys(
        ForeignKeyReconciliationRequest(
            source_layer="gold",
            reference_layer="gold",
            mutation_layer="gold",
            source_table="chembl.assay",
            reference_table="chembl.target",
            source_key="target_id",
            reference_key="target_id",
            primary_keys=("assay_id",),
            dry_run=True,
        )
    )

    assert result.dry_run is True
    assert result.would_mutate is True
    assert result.mutated is False
    assert result.orphan_rows_deleted == 1
    assert quarantine.writes == []


@pytest.mark.asyncio
async def test_gold_reference_table_missing_fails_fast() -> None:
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverWriter(),  # type: ignore[arg-type]
        gold_writer=_GoldReader(
            {
                "chembl.assay": [
                    {
                        "assay_id": "CHEMBL_A1",
                        "target_id": "CHEMBL_T999",
                        "_is_current": True,
                    }
                ],
            }
        ),
        logger=_Logger(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="reference table not found"):
        await adapter.reconcile_foreign_keys(
            ForeignKeyReconciliationRequest(
                source_layer="gold",
                reference_layer="gold",
                mutation_layer="gold",
                source_table="chembl.assay",
                reference_table="chembl.target",
                source_key="target_id",
                reference_key="target_id",
                primary_keys=("assay_id",),
            )
        )
