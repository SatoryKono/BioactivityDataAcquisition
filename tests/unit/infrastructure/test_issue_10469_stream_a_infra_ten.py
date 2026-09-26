"""Stream A silver/quarantine/delta leftovers (no gold_writer import)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.workflow import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.delta.arrow_converter import (
    ArrowDataConverter,
    build_arrow_schema_preparation_context,
    filter_record_for_schema,
)
from bioetl.infrastructure.storage.delta import table_ops
from bioetl.infrastructure.storage.delta.table_ops import (
    _read_records_from_active_parquet_files,
    clear_delta_tables,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.storage.delta_reader_helpers import (
    count_delta_rows,
    try_native_delta_row_count,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.silver.delta_merge_helpers import (
    _build_merge_execute_callable,
    _build_merge_update_predicate,
    _delta_table_has_parquet_data,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
    _delete_silver_orphan_rows_once,
    _delta_table_column_names,
    apply_reconciliation_mutation,
    delete_silver_orphan_rows,
    expire_gold_orphan_rows,
)

pytestmark = pytest.mark.unit


def _fk_request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload: dict[str, object] = {
        "source_table": "src",
        "reference_table": "ref",
        "source_key": "parent_id",
        "reference_key": "id",
        "primary_keys": ("id",),
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)


class _MergeChain:
    def when_matched_delete(self) -> _MergeChain:
        return self

    def when_matched_update(self, updates: dict[str, str]) -> _MergeChain:
        self.updates = updates
        return self

    def execute(self) -> dict[str, int]:
        return {"rows": 1}


class _FakeDeltaTable:
    def __init__(self, path: str) -> None:
        self.path = path

    def merge(self, **_kwargs: object) -> _MergeChain:
        return _MergeChain()

    def schema(self) -> SimpleNamespace:
        return SimpleNamespace(
            to_arrow=lambda: pa.schema(
                [
                    ("id", pa.string()),
                    ("_is_current", pa.bool_()),
                    ("_valid_to", pa.string()),
                ]
            )
        )


def _complete_request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload: dict[str, object] = {
        "reference_completeness": "complete",
        "reference_identity": "ref",
        "completeness_evidence_ref": "evidence://ref",
    }
    payload.update(overrides)
    return _fk_request(**payload)


class TestQuarantineMutationLeftovers:
    async def test_silver_delete_and_apply_mutation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = SimpleNamespace(DeltaTable=_FakeDeltaTable)
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine._load_deltalake_module",
            lambda: module,
        )
        host = SimpleNamespace(
            silver_writer=SimpleNamespace(
                _resolve_table_path=lambda name: f"/silver/{name}"
            ),
            gold_writer=None,
            logger=MagicMock(),
            clock=SimpleNamespace(now=lambda: datetime(2024, 1, 1, tzinfo=UTC)),
            quarantine=SimpleNamespace(write_many=AsyncMock()),
            quarantine_pipeline_name="workflow",
        )
        request = _complete_request()
        orphans = [{"id": "1", "parent_id": "missing"}]
        executed = _delete_silver_orphan_rows_once(
            module, "/silver/src", [{"id": "1"}], "target.id = source.id"
        )
        assert executed == {"rows": 1}
        await delete_silver_orphan_rows(host, request, orphan_rows=orphans)
        summary = await apply_reconciliation_mutation(
            host, request, orphan_rows=orphans
        )
        assert summary.mutation_mode == "silver_rewrite"
        host.quarantine.write_many.assert_awaited()

    async def test_gold_expiry_inspects_schema_without_gold_writer_module(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = SimpleNamespace(
            DeltaTable=_FakeDeltaTable,
            GOLD_WRITE_RETRY_ERRORS=(),
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine.load_gold_writer_module",
            lambda: module,
        )

        async def _run_in_executor(fn: object, *args: object) -> object:
            return fn(*args) if callable(fn) else None

        gold = SimpleNamespace(
            _resolve_table_path=lambda name: f"/gold/{name}",
            _run_in_executor=_run_in_executor,
        )
        host = SimpleNamespace(
            silver_writer=SimpleNamespace(
                _resolve_table_path=lambda name: f"/silver/{name}"
            ),
            gold_writer=gold,
            logger=MagicMock(),
            clock=SimpleNamespace(now=lambda: datetime(2024, 1, 1, tzinfo=UTC)),
            quarantine=None,
            quarantine_pipeline_name=None,
        )
        names = await _delta_table_column_names(module, "/gold/src", logger=host.logger)
        assert names is not None
        assert "id" in names
        request = _complete_request(source_layer="gold", mutation_layer="gold")
        orphans = [
            {
                "id": "1",
                "parent_id": "missing",
                "_is_current": True,
                "_valid_to": None,
            }
        ]
        await expire_gold_orphan_rows(host, request, orphan_rows=orphans)
        summary = await apply_reconciliation_mutation(
            host, request, orphan_rows=orphans
        )
        assert summary.mutation_mode == "gold_scd2_expiry"


class TestForeignKeyAdapterLeftovers:
    async def test_no_orphans_and_gold_snapshot_warning(self) -> None:
        logger = MagicMock()

        class _MatchingSilver:
            async def read_silver(self, table: str, columns=None):
                del columns
                if table == "src":
                    return [{"id": "1", "parent_id": "p"}]
                return [{"id": "p"}]

        adapter = SilverForeignKeyReconciliationAdapter(
            silver_writer=_MatchingSilver(),  # type: ignore[arg-type]
            logger=logger,
        )
        result = await adapter.reconcile_foreign_keys(_complete_request())
        assert result.mutation_mode == "no_op"
        assert result.orphan_rows_deleted == 0

        class _GoldSnap:
            async def read_gold(
                self, table_name: str, columns=None, current_only: bool = True
            ):
                del columns, current_only
                return [{"id": "1", "parent_id": "p", "_is_current": True}]

            async def read_reconciliation_snapshot(
                self, table_name: str
            ) -> dict[str, int]:
                del table_name
                raise ValueError("snapshot unavailable")

        gold_adapter = SilverForeignKeyReconciliationAdapter(
            silver_writer=_MatchingSilver(),  # type: ignore[arg-type]
            logger=logger,
            gold_writer=_GoldSnap(),  # type: ignore[arg-type]
        )
        gold_result = await gold_adapter.reconcile_foreign_keys(
            _complete_request(source_layer="gold", reference_layer="silver")
        )
        assert gold_result.source_snapshot is None
        logger.warning.assert_any_call(
            "Reconciliation snapshot unavailable",
            error_type="ValueError",
        )

        class _GoldOk:
            async def read_gold(
                self, table_name: str, columns=None, current_only: bool = True
            ):
                del columns, current_only
                return [{"id": "1", "parent_id": "p", "_is_current": True}]

            async def read_reconciliation_snapshot(
                self, table_name: str
            ) -> dict[str, int]:
                del table_name
                return {"version": 3, "physical_rows": 2, "current_rows": 1}

        ok_adapter = SilverForeignKeyReconciliationAdapter(
            silver_writer=_MatchingSilver(),  # type: ignore[arg-type]
            logger=logger,
            gold_writer=_GoldOk(),  # type: ignore[arg-type]
        )
        snapped = await ok_adapter.reconcile_foreign_keys(
            _complete_request(source_layer="gold", reference_layer="silver")
        )
        assert snapped.source_snapshot == {
            "version": 3,
            "physical_rows": 2,
            "current_rows": 1,
        }


class TestArrowConverterLeftovers:
    def test_filter_missing_keys_and_sanitize_cast_fallback(self) -> None:
        schema = pa.schema([("id", pa.string()), ("payload", pa.string())])
        context = build_arrow_schema_preparation_context(schema)
        filtered = filter_record_for_schema({"id": "1", "noise": 1}, context)
        assert filtered == {"id": "1"}
        converter = ArrowDataConverter()
        col = pa.array([1, 2], type=pa.int64())
        sanitized, effective = converter._sanitize_single_null_column(
            col, pa.int64(), pa.list_(pa.string())
        )
        assert pa.types.is_string(effective) or pa.types.is_list(effective)
        assert len(sanitized) == 2
        nullish = converter.convert_records_to_arrow(
            [{"id": "a", "empty": None}, {"id": "b", "empty": None}]
        )
        assert nullish.num_rows == 2


class TestDeltaReaderAndTableOpsLeftovers:
    async def test_read_table_native_count_and_to_table(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reader = DeltaReader(tmp_path, NoOpLogger())

        class _Scanner:
            def __init__(self, *, with_to_table: bool) -> None:
                self._with_to_table = with_to_table

            def head(self, n: int) -> pa.Table:
                return pa.table({"id": list(range(n))})

            def to_table(self) -> pa.Table:
                return pa.table({"id": [7, 8]})

        class _Dataset:
            def __init__(self, *, with_to_table: bool) -> None:
                self._with_to_table = with_to_table

            def scanner(self, columns=None) -> _Scanner:
                del columns
                return _Scanner(with_to_table=self._with_to_table)

        class _CountedDelta:
            def count(self) -> int:
                return 2

            def to_pyarrow_dataset(self) -> _Dataset:
                return _Dataset(with_to_table=True)

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta_reader.DeltaTable",
            lambda *_a, **_k: _CountedDelta(),
        )
        counted = await reader.read_table("chembl/activity")
        assert counted.column("id").to_pylist() == [0, 1]

        class _NoCountDelta:
            def to_pyarrow_dataset(self) -> _Dataset:
                return _Dataset(with_to_table=True)

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta_reader.DeltaTable",
            lambda *_a, **_k: _NoCountDelta(),
        )
        full = await reader.read_table("chembl/activity")
        assert full.column("id").to_pylist() == [7, 8]

        class _HeadOnlyScanner:
            def head(self, n: int) -> pa.Table:
                return pa.table({"id": [n]})

        class _HeadOnlyDataset:
            def scanner(self, columns=None) -> _HeadOnlyScanner:
                del columns
                return _HeadOnlyScanner()

        class _HeadOnlyDelta:
            def to_pyarrow_dataset(self) -> _HeadOnlyDataset:
                return _HeadOnlyDataset()

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta_reader.DeltaTable",
            lambda *_a, **_k: _HeadOnlyDelta(),
        )
        fallback = await reader.read_table("chembl/activity")
        assert fallback.num_rows == 1

    def test_native_count_and_table_ops_concat(self, tmp_path: Path) -> None:
        class _Boom:
            def count(self) -> int:
                raise DeltaTableNotFoundError("gone")

        assert try_native_delta_row_count(_Boom()) is None  # type: ignore[arg-type]

        class _Keyboard:
            def count(self) -> int:
                raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            count_delta_rows(
                _Keyboard(),  # type: ignore[arg-type]
                resolved_path=tmp_path,
                delta_table_factory=lambda _p: SimpleNamespace(
                    to_pyarrow_table=lambda columns=None: pa.table({"id": [1]})
                ),
            )

        first = tmp_path / "a.parquet"
        second = tmp_path / "b.parquet"
        import pyarrow.parquet as pq

        pq.write_table(pa.table({"id": ["1"]}), first)
        pq.write_table(pa.table({"id": ["2"]}), second)
        table = SimpleNamespace(file_uris=lambda: [str(first), str(second)])
        rows = _read_records_from_active_parquet_files(table)
        assert [row["id"] for row in rows] == ["1", "2"]

        present = tmp_path / "delta"
        present.mkdir()
        (present / "_delta_log").mkdir()
        assert (
            clear_delta_tables(base_path=tmp_path, table_path=present, dry_run=False)
            == 1
        )
        assert not present.exists()

    def test_merge_execute_callable_without_parquet(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "empty-delta"
        empty.mkdir()
        assert _delta_table_has_parquet_data(str(empty)) is False

        def _write(table_path: str, records: object, **kwargs: object) -> str:
            del table_path, records, kwargs
            return "written"

        import sys

        monkeypatch.setattr(
            sys.modules["deltalake"], "write_deltalake", _write, raising=False
        )
        records = pa.table({"id": ["1"], "content_hash": ["abc"]})
        execute = _build_merge_execute_callable(
            dt=SimpleNamespace(),  # type: ignore[arg-type]
            table_path=str(empty),
            records=records,
            merge_condition="target.id = source.id",
            merge_schema=True,
        )
        assert execute() == "written"
        execute_plain = _build_merge_execute_callable(
            dt=SimpleNamespace(),  # type: ignore[arg-type]
            table_path=str(empty),
            records=pa.table({"id": ["1"]}),
            merge_condition="target.id = source.id",
            merge_schema=False,
        )
        assert execute_plain() == "written"
        assert _build_merge_update_predicate(pa.table({"id": ["1"]})) == "true"
        assert table_ops.DeltaTable is not None
