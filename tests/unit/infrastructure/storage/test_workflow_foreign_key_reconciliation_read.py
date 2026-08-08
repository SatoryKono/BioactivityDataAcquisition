# pyright: reportArgumentType=false
"""Unit tests for FK reconciliation typed seams and current_only filtering (#7995)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    GoldReconciliationReaderProtocol,
    ReconcileDebugArtifactSinkProtocol,
    SilverForeignKeyReconciliationAdapter,
    filter_current_rows,
)

pytestmark = pytest.mark.unit


def test_filter_current_rows_keeps_all_when_no_flag_column() -> None:
    rows = [{"id": "1"}, {"id": "2"}]
    assert filter_current_rows(rows, current_only=True, layer="silver") == rows


def test_filter_current_rows_honors_is_current_flag() -> None:
    rows = [
        {"id": "cur", "_is_current": True},
        {"id": "hist", "_is_current": False},
        {"id": "one", "_is_current": 1},
    ]
    filtered = filter_current_rows(rows, current_only=True, layer="silver")
    assert {row["id"] for row in filtered} == {"cur", "one"}


def test_filter_current_rows_disabled_returns_all() -> None:
    rows = [
        {"id": "cur", "_is_current": True},
        {"id": "hist", "_is_current": False},
    ]
    assert filter_current_rows(rows, current_only=False, layer="silver") == rows


@dataclass
class _SilverWriter:
    rows_by_table: dict[str, list[dict[str, object]]] = field(default_factory=dict)

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, object]]:
        rows = self.rows_by_table[table_name]
        if columns is None:
            return [dict(row) for row in rows]
        return [{c: row.get(c) for c in columns} for row in rows]


@dataclass
class _Logger:
    def info(self, message: str, **context: object) -> None:
        del message, context

    def warning(self, message: str, **context: object) -> None:
        del message, context


@dataclass
class _GoldReader:
    rows_by_table: dict[str, list[dict[str, object]]]

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, object]]:
        rows = [dict(row) for row in self.rows_by_table[table_name]]
        if current_only:
            rows = filter_current_rows(rows, current_only=True, layer="gold")
        if columns is None:
            return rows
        return [{c: row.get(c) for c in columns} for row in rows]


def test_gold_reader_port_structural_match() -> None:
    reader = _GoldReader(rows_by_table={})
    assert isinstance(reader, GoldReconciliationReaderProtocol)


@pytest.mark.asyncio
async def test_silver_read_applies_current_only_flag() -> None:
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverWriter(  # type: ignore[arg-type]
            rows_by_table={
                "activity": [
                    {"activity_id": "a1", "assay_id": "x", "_is_current": True},
                    {"activity_id": "a2", "assay_id": "y", "_is_current": False},
                ],
                "assay": [
                    {"assay_id": "x"},
                ],
            }
        ),
        logger=_Logger(),  # type: ignore[arg-type]
    )
    result = await adapter.reconcile_foreign_keys(
        ForeignKeyReconciliationRequest(
            source_table="activity",
            reference_table="assay",
            source_key="assay_id",
            reference_key="assay_id",
            primary_keys=("activity_id",),
            dry_run=True,
        )
    )
    # Only current source row is scanned; hist row filtered out by current_only.
    assert result.scanned_rows == 1
    assert result.orphan_rows_deleted == 0


def test_artifact_sink_port_is_runtime_checkable() -> None:
    class _Sink:
        def write_reconcile_debug_artifacts(
            self, **kwargs: object
        ) -> tuple[object, ...]:
            del kwargs
            return ()

    assert isinstance(_Sink(), ReconcileDebugArtifactSinkProtocol)
