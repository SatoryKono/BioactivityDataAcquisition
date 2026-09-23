# pyright: reportArgumentType=false
"""Unit tests covering FK-reconciliation partial modules (#10631 / AUD-004).

Imports the owner modules directly so coverage attributes hits to
``workflow_foreign_key_reconciliation_{loaded,normalization,reads}`` rather
than the support re-export facade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_loaded import (
    reconcile_loaded_rows,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_normalization import (
    NULL_TOKEN,
    normalize_row_key,
    normalize_value,
    row_has_null_foreign_key,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    GoldReconciliationReaderProtocol,
    GoldSnapshotReaderProtocol,
    _current_flag_column,
    _is_current_flag_value,
    filter_current_rows,
    read_reference_rows,
    read_rows,
    read_source_rows,
)

pytestmark = pytest.mark.unit


def _complete_request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload: dict[str, object] = {
        "source_table": "silver.activity",
        "reference_table": "silver.assay",
        "source_key": "assay_id",
        "reference_key": "assay_id",
        "primary_keys": ("activity_id",),
        "reference_completeness": "complete",
        "reference_identity": "silver.assay",
        "completeness_evidence_ref": "tests/unit/fk-reference-complete",
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)  # type: ignore[arg-type]


@dataclass
class _LoadedHost:
    metrics: list[tuple[int, int, int]] = field(default_factory=list)
    logs: list[tuple[str, str]] = field(default_factory=list)
    artifacts: list[object] = field(default_factory=list)

    def _record_metrics(self, *, scanned: int, retained: int, deleted: int) -> None:
        self.metrics.append((scanned, retained, deleted))

    def _log(self, level: str, message: str, **context: object) -> None:
        del context
        self.logs.append((level, message))

    def _write_debug_artifacts(
        self,
        request: ForeignKeyReconciliationRequest,
        result: object,
        *,
        retained_rows: list[dict[str, object]],
        orphan_rows: list[dict[str, object]],
    ) -> None:
        self.artifacts.append((request, result, retained_rows, orphan_rows))


@dataclass
class _SilverWriter:
    rows_by_table: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, object]]:
        if table_name in self.missing:
            raise FileNotFoundError(table_name)
        rows = self.rows_by_table[table_name]
        if columns is None:
            return [dict(row) for row in rows]
        return [{column: row.get(column) for column in columns} for row in rows]


@dataclass
class _AsyncGoldReader:
    rows_by_table: dict[str, list[dict[str, object]]] = field(default_factory=dict)

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, object]]:
        del current_only
        rows = [dict(row) for row in self.rows_by_table[table_name]]
        if columns is None:
            return rows
        return [{column: row.get(column) for column in columns} for row in rows]


@dataclass
class _SyncGoldReader:
    rows_by_table: dict[str, list[dict[str, object]]] = field(default_factory=dict)

    def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, object]]:
        del current_only
        rows = [dict(row) for row in self.rows_by_table[table_name]]
        if columns is None:
            return rows
        return [{column: row.get(column) for column in columns} for row in rows]


@dataclass
class _ReadsHost:
    silver_writer: _SilverWriter
    gold_writer: object | None = None
    metrics: list[tuple[int, int, int]] = field(default_factory=list)
    logs: list[tuple[str, str]] = field(default_factory=list)

    def _record_metrics(self, *, scanned: int, retained: int, deleted: int) -> None:
        self.metrics.append((scanned, retained, deleted))

    def _log(self, level: str, message: str, **context: object) -> None:
        del context
        self.logs.append((level, message))


class _Blank:
    def __str__(self) -> str:
        return "  "


class _Named:
    def __str__(self) -> str:
        return "token"


def test_normalize_value_covers_null_bool_numeric_string_and_other() -> None:
    assert normalize_value(None) is None
    assert normalize_value(True) == ("bool", True)
    assert normalize_value(False) == ("bool", False)
    assert normalize_value(float("nan")) is None
    assert normalize_value(5.0) == ("int", 5)
    assert normalize_value(1.25) == ("float", 1.25)
    assert normalize_value(7) == ("int", 7)
    assert normalize_value("  ") is None
    assert normalize_value("  assay-1  ") == ("str", "assay-1")
    assert normalize_value(_Blank()) is None
    other = normalize_value(_Named())
    assert other == ("other", "_Named", "token")


def test_normalize_row_key_and_null_foreign_key_helpers() -> None:
    row = {"assay_id": "A1", "parent_id": None}
    assert row_has_null_foreign_key(row, ("parent_id",)) is True
    assert row_has_null_foreign_key(row, ("assay_id",)) is False
    equal_nulls = normalize_row_key(row, ("parent_id",), nulls_equal=True)
    assert equal_nulls == (NULL_TOKEN,)
    assert normalize_row_key(row, ("parent_id",), nulls_equal=False) is None
    assert normalize_row_key(row, ("assay_id",), nulls_equal=False) == (("str", "A1"),)


@pytest.mark.asyncio
async def test_reconcile_loaded_rows_blocks_unproven_reference() -> None:
    host = _LoadedHost()
    result = await reconcile_loaded_rows(
        host,
        _complete_request(reference_completeness="unproven"),
        source_rows=[
            {"activity_id": "a1", "assay_id": "missing"},
            {"activity_id": "a2", "assay_id": "ok"},
        ],
        reference_rows=[{"assay_id": "ok"}],
    )
    assert result.mutated is False
    assert result.would_mutate is False
    assert result.mutation_mode == "blocked"
    assert result.mutation_blocked_reason == "reference_completeness_unproven"
    assert result.unproven_unmatched_rows == 1
    assert result.orphan_rows_deleted == 0
    assert host.metrics[-1] == (2, 2, 0)
    assert host.artifacts


@pytest.mark.asyncio
async def test_reconcile_loaded_rows_completes_without_orphans() -> None:
    host = _LoadedHost()
    result = await reconcile_loaded_rows(
        host,
        _complete_request(),
        source_rows=[{"activity_id": "a1", "assay_id": "ok"}],
        reference_rows=[{"assay_id": "ok"}],
    )
    assert result.mutated is False
    assert result.orphan_rows_deleted == 0
    assert result.retained_rows == 1
    assert host.metrics[-1] == (1, 1, 0)


@pytest.mark.asyncio
async def test_reconcile_loaded_rows_dry_run_preview() -> None:
    host = _LoadedHost()
    result = await reconcile_loaded_rows(
        host,
        _complete_request(dry_run=True),
        source_rows=[{"activity_id": "a1", "assay_id": "missing"}],
        reference_rows=[{"assay_id": "ok"}],
    )
    assert result.would_mutate is True
    assert result.mutated is False
    assert result.orphan_rows_deleted == 1


@pytest.mark.asyncio
async def test_reconcile_loaded_rows_mutates_orphans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _LoadedHost()
    summary = SimpleNamespace(
        mutation_mode="silver_rewrite",
        quarantine_batch_id="q-10631",
        quarantine_rows_written=1,
        quarantine_error_code=None,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_loaded.apply_reconciliation_mutation",
        AsyncMock(return_value=summary),
    )
    result = await reconcile_loaded_rows(
        host,
        _complete_request(dry_run=False),
        source_rows=[{"activity_id": "a1", "assay_id": "missing"}],
        reference_rows=[{"assay_id": "ok"}],
    )
    assert result.mutated is True
    assert result.mutation_mode == "silver_rewrite"
    assert result.quarantine_batch_id == "q-10631"
    assert host.logs
    assert host.artifacts


def test_current_flag_helpers_cover_empty_missing_and_value_shapes() -> None:
    assert _current_flag_column([]) is None
    assert _current_flag_column([{"id": "1"}]) is None
    assert _current_flag_column([{"id": "1", "is_current": True}]) == "is_current"
    assert _is_current_flag_value(True) is True
    assert _is_current_flag_value(False) is False
    assert _is_current_flag_value(None) is False
    assert _is_current_flag_value(1) is True
    assert _is_current_flag_value(1.0) is True
    assert _is_current_flag_value(0) is False
    assert _is_current_flag_value("yes") is True
    assert _is_current_flag_value("TRUE") is True
    assert _is_current_flag_value("no") is False
    assert _is_current_flag_value(object()) is False


def test_filter_current_rows_empty_disabled_and_is_current_alias() -> None:
    empty: list[dict[str, object]] = []
    assert filter_current_rows(empty, current_only=True, layer="silver") == empty
    rows = [
        {"id": "cur", "is_current": "1"},
        {"id": "hist", "is_current": "0"},
    ]
    assert filter_current_rows(rows, current_only=False, layer="gold") == rows
    filtered = filter_current_rows(rows, current_only=True, layer="gold")
    assert [row["id"] for row in filtered] == ["cur"]


@pytest.mark.asyncio
async def test_read_source_rows_skips_missing_silver_table() -> None:
    host = _ReadsHost(silver_writer=_SilverWriter(missing={"activity"}))
    skipped = await read_source_rows(host, _complete_request(source_table="activity"))
    assert skipped is None
    assert host.metrics == [(0, 0, 0)]
    assert host.logs and host.logs[0][0] == "warning"


@pytest.mark.asyncio
async def test_read_reference_rows_wraps_missing_table_for_reads_host() -> None:
    host = _ReadsHost(silver_writer=_SilverWriter(missing={"assay"}))
    with pytest.raises(ValueError, match="reference table not found"):
        await read_reference_rows(host, _complete_request(reference_table="assay"))


@pytest.mark.asyncio
async def test_read_source_and_reference_rows_from_silver() -> None:
    host = _ReadsHost(
        silver_writer=_SilverWriter(
            rows_by_table={
                "activity": [
                    {"activity_id": "a1", "assay_id": "ok", "_is_current": True},
                    {"activity_id": "a2", "assay_id": "y", "_is_current": False},
                ],
                "assay": [{"assay_id": "ok"}],
            }
        )
    )
    source = await read_source_rows(host, _complete_request(source_table="activity"))
    assert source is not None
    assert [row["activity_id"] for row in source] == ["a1"]
    reference = await read_reference_rows(
        host, _complete_request(reference_table="assay")
    )
    assert reference == [{"assay_id": "ok"}]


@pytest.mark.asyncio
async def test_read_rows_requires_gold_writer_and_accepts_sync_reader() -> None:
    missing_gold = _ReadsHost(silver_writer=_SilverWriter())
    with pytest.raises(ValueError, match="configured gold_writer"):
        await read_rows(
            missing_gold,
            layer="gold",
            table_name="chembl.assay",
            columns=None,
            current_only=True,
        )

    host = _ReadsHost(
        silver_writer=_SilverWriter(),
        gold_writer=_SyncGoldReader(
            rows_by_table={
                "chembl.assay": [
                    {"assay_id": "cur", "is_current": True},
                    {"assay_id": "hist", "is_current": False},
                ]
            }
        ),
    )
    rows = await read_rows(
        host,
        layer="gold",
        table_name="chembl.assay",
        columns=None,
        current_only=True,
    )
    assert [row["assay_id"] for row in rows] == ["cur"]


@pytest.mark.asyncio
async def test_read_rows_awaitable_gold_reader() -> None:
    host = _ReadsHost(
        silver_writer=_SilverWriter(),
        gold_writer=_AsyncGoldReader(
            rows_by_table={"chembl.target": [{"target_id": "T1"}]}
        ),
    )
    rows = await read_rows(
        host,
        layer="gold",
        table_name="chembl.target",
        columns=["target_id"],
        current_only=False,
    )
    assert rows == [{"target_id": "T1"}]


def test_gold_reader_protocols_are_runtime_checkable() -> None:
    assert isinstance(_AsyncGoldReader(), GoldReconciliationReaderProtocol)
    assert isinstance(_SyncGoldReader(), GoldReconciliationReaderProtocol)

    class _Snapshot:
        async def read_reconciliation_snapshot(self, table_name: str) -> dict[str, int]:
            del table_name
            return {}

    assert isinstance(_Snapshot(), GoldSnapshotReaderProtocol)
