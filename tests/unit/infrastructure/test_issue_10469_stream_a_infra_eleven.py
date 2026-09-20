"""Stream A gold leftovers: gold_writer and gold helpers (no silver_writer/deltalake import)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from typing import Any

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.gold import io_delta_runtime as gold_runtime
from bioetl.infrastructure.storage.gold import read_cleanup_mixin as gold_cleanup
from bioetl.infrastructure.storage.gold.io_delta_runtime import (
    _PreparedSimpleGoldWrite,
    _SimpleGoldWriteRequest,
    _execute_prepared_simple_gold_write,
)
from bioetl.infrastructure.storage.gold.io_metrics import _split_gold_merged_table_label
from bioetl.infrastructure.storage.gold.io_preparation import _prepare_gold_merged_table
from bioetl.infrastructure.storage.gold.read_cleanup_mixin import (
    GoldWriterReadCleanupMixin,
)
from bioetl.infrastructure.storage.gold.writer_metrics import _split_gold_table_label
from bioetl.infrastructure.storage.gold_writer import write_deltalake

pytestmark = pytest.mark.unit


class _GoldReadHost(GoldWriterReadCleanupMixin):
    def __init__(self, table_path: str) -> None:
        self._table_path = table_path

    def _resolve_table_path(self, table_name: str) -> str:
        del table_name
        return self._table_path

    async def _run_in_executor(self, fn: Any, *args: object) -> object:
        return fn(*args)


class TestGoldReadCleanupLeftovers:
    def test_projection_and_current_flag_helpers(self) -> None:
        assert (
            gold_cleanup._build_read_projection(columns=None, current_only=True) is None
        )
        assert (
            gold_cleanup._build_read_projection(columns=["id"], current_only=True)
            is None
        )
        assert gold_cleanup._build_read_projection(
            columns=["id", "name"], current_only=False
        ) == ["id", "name"]
        assert gold_cleanup._current_flag_column(["id", "is_current"]) == "is_current"
        assert gold_cleanup._current_flag_column(["id"]) is None

    async def test_read_gold_projection_history_and_preview(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        table_dir = tmp_path / "gold" / "activity"
        table_dir.mkdir(parents=True)
        (table_dir / "part.parquet").write_bytes(b"x")

        class _Delta:
            def __init__(self, path: str) -> None:
                self.path = path

            def to_pyarrow_table(self, columns: list[str] | None = None) -> pa.Table:
                table = pa.table(
                    {
                        "id": ["1", "2"],
                        "is_current": [True, False],
                        "valid_from": ["2020-01-01", "2021-01-01"],
                    }
                )
                if columns:
                    return table.select(columns)
                return table

            def to_pyarrow_dataset(self) -> SimpleNamespace:
                schema_names = ["id", "is_current"]

                class _Dataset:
                    schema = SimpleNamespace(names=schema_names)

                    def count_rows(self, filter=None) -> int:
                        return 2 if filter is None else 1

                return _Dataset()

            def version(self) -> int:
                return 4

        monkeypatch.setattr(
            gold_cleanup,
            "_load_gold_writer_module",
            lambda: SimpleNamespace(DeltaTable=_Delta),
        )
        host = _GoldReadHost(str(table_dir))
        projected = await host.read_gold("activity", columns=["id"], current_only=False)
        assert projected == [{"id": "1"}, {"id": "2"}]
        current = await host.read_gold("activity", current_only=True)
        assert [row["id"] for row in current] == ["1"]
        history = await host.get_history(
            "activity", business_key_values={"id": "1"}, limit=1
        )
        assert history
        preview = host.preview_cleanup("activity")
        assert preview["exists"] is True
        assert preview["file_count"] >= 1
        assert preview["layer"] == "gold"
        snapshot = await host.read_reconciliation_snapshot("activity")
        assert snapshot["version"] == 4
        assert snapshot["physical_rows"] == 2


class TestGoldWriterSeamLeftovers:
    def test_write_deltalake_normalizes_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict[str, object]] = []

        def _write_deltalake(
            *,
            table_or_uri: object,
            data: object,
            partition_by: object,
            mode: object,
            schema_mode: object,
        ) -> None:
            calls.append(
                {
                    "table_or_uri": table_or_uri,
                    "data": data,
                    "partition_by": partition_by,
                    "mode": mode,
                    "schema_mode": schema_mode,
                }
            )

        monkeypatch.setattr(
            sys.modules["deltalake"],
            "write_deltalake",
            _write_deltalake,
            raising=False,
        )
        table = pa.table({"id": ["1"]})
        write_deltalake(
            tmp_path / "gold-table",
            table,
            partition_by=["pipeline"],
            mode="overwrite",
            schema_mode="overwrite",
        )
        assert calls
        assert calls[0]["mode"] == "overwrite"
        assert calls[0]["schema_mode"] == "overwrite"
        assert calls[0]["partition_by"] == ["pipeline"]


class TestGoldRuntimeLeftovers:
    async def test_simple_write_exports_csv_and_empty_retry(self) -> None:
        exporter = SimpleNamespace(export=AsyncMock())

        async def _run_in_executor(*_args: object, **_kwargs: object) -> None:
            return None

        host = SimpleNamespace(
            _run_in_executor=_run_in_executor,
            csv_exporter=exporter,
        )
        prepared = _PreparedSimpleGoldWrite(
            request=_SimpleGoldWriteRequest(
                table_path="/gold/t",
                table_name="chembl/activity",
                records=[{"id": "1"}],
                mode="overwrite",
                partition_cols=None,
                primary_keys=["id"],
            ),
            arrow_data=pa.table({"id": ["1"]}),
            schema_mode="overwrite",
        )
        module = SimpleNamespace(GOLD_WRITE_RETRY_ERRORS=())
        await _execute_prepared_simple_gold_write(host, module, prepared)
        exporter.export.assert_awaited()
        append_prepared = _PreparedSimpleGoldWrite(
            request=_SimpleGoldWriteRequest(
                table_path="/gold/t",
                table_name="chembl/activity",
                records=[{"id": "1"}],
                mode="append",
                partition_cols=None,
                primary_keys=["id"],
            ),
            arrow_data=pa.table({"id": ["1"]}),
            schema_mode=None,
        )
        await _execute_prepared_simple_gold_write(host, module, append_prepared)
        assert exporter.export.await_count == 2

    def test_extend_retry_errors_without_pyarrow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        saved = sys.modules.get("pyarrow")
        monkeypatch.setitem(sys.modules, "pyarrow", None)
        try:
            extended = gold_runtime._extend_retry_errors_with_arrow((OSError,))
            assert extended == (OSError,)
        finally:
            if saved is not None:
                sys.modules["pyarrow"] = saved

    def test_split_labels_and_ingestion_ts_drop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.gold.io_preparation._load_gold_writer_module",
            lambda: SimpleNamespace(coerce_null_types_for_delta=lambda table: table),
        )
        table = _prepare_gold_merged_table(
            records=[
                {"id": "b", "_ingestion_ts": "ts"},
                {"id": "a", "_ingestion_ts": "ts"},
            ],
            primary_keys=["id"],
            preserve_column_order=True,
        )
        assert "_ingestion_ts" not in table.column_names
        assert _split_gold_merged_table_label("") == ("unknown", "unknown")
        assert _split_gold_table_label("") == ("unknown", "unknown")
