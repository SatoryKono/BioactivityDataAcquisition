"""Delta reader/table_ops/retention residuals without gold_writer."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pytest
from deltalake.exceptions import CommitFailedError, DeltaError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import DeltaWriteConflictError, TableNotFoundError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta import table_ops
from bioetl.infrastructure.storage.delta.table_ops import (
    _can_use_pyarrow_dataset_scanner,
    _read_records_from_active_parquet_files,
    clear_delta_tables,
    get_delta_table_arrow_schema,
    load_delta_table,
    normalize_delta_filesystem_path,
    read_delta_records,
    resolve_delta_table_path,
    resolve_parquet_file_uri,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.storage.delta_reader_helpers import (
    count_delta_rows,
    try_native_delta_row_count,
)
from bioetl.infrastructure.storage.support import retention_dedup as dedup

pytestmark = pytest.mark.unit


class TestTableOps:
    def test_path_and_uri_helpers(self, tmp_path: Path) -> None:
        assert _can_use_pyarrow_dataset_scanner(platform="win32") is False
        assert _can_use_pyarrow_dataset_scanner(platform="linux") is True
        assert resolve_parquet_file_uri("s3://bucket/a.parquet") == "s3://bucket/a.parquet"
        assert resolve_parquet_file_uri("file:///C:/tmp/a.parquet") == "C:/tmp/a.parquet"
        assert resolve_parquet_file_uri("file:///tmp/a.parquet") == "/tmp/a.parquet"
        remote = normalize_delta_filesystem_path("s3://bucket/table/")
        assert remote == "s3://bucket/table"
        local = normalize_delta_filesystem_path(tmp_path / "delta")
        assert local.endswith("delta")
        nested = resolve_delta_table_path(
            base_path=str(tmp_path),
            table_name="chembl.activity",
            flat_structure=False,
        )
        assert nested.endswith("chembl/activity") or nested.endswith("chembl\\activity")
        flat = resolve_delta_table_path(
            base_path=str(tmp_path),
            table_name="ignored",
            flat_structure=True,
        )
        assert Path(flat) == tmp_path or flat.replace("\\", "/").endswith(tmp_path.as_posix())
        remote_nested = resolve_delta_table_path(
            base_path="s3://bucket/root/",
            table_name="chembl.activity",
            flat_structure=False,
        )
        assert remote_nested == "s3://bucket/root/chembl/activity"
        remote_flat = resolve_delta_table_path(
            base_path="s3://bucket/root",
            table_name="chembl.activity",
            flat_structure=True,
        )
        assert remote_flat == "s3://bucket/root"

    def test_read_records_empty_and_schema(self) -> None:
        empty = SimpleNamespace(file_uris=lambda: [])
        assert _read_records_from_active_parquet_files(empty) == []
        assert read_delta_records(empty) == []
        schema = pa.schema([("id", pa.string())])
        table = SimpleNamespace(schema=lambda: SimpleNamespace(to_arrow=lambda: schema))
        converted = get_delta_table_arrow_schema(table)
        assert converted.names == ["id"]

    def test_load_delta_table_uses_delta_ctor(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        created: list[str] = []

        class _FakeDelta:
            def __init__(self, path: str) -> None:
                created.append(path)

        monkeypatch.setattr(table_ops, "DeltaTable", _FakeDelta)
        loaded = load_delta_table(str(tmp_path / "tbl"))
        assert isinstance(loaded, _FakeDelta)
        assert created

    def test_clear_delta_tables(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope"
        assert clear_delta_tables(base_path=missing, table_path=None, dry_run=False) == 0
        table_dir = tmp_path / "chembl"
        table_dir.mkdir()
        (table_dir / "_delta_log").mkdir()
        other = tmp_path / "not-delta"
        other.mkdir()
        assert (
            clear_delta_tables(base_path=tmp_path, table_path=None, dry_run=True) == 1
        )
        assert table_dir.exists()
        cleared = clear_delta_tables(base_path=tmp_path, table_path=None, dry_run=False)
        assert cleared == 1
        assert not table_dir.exists()
        gone = tmp_path / "already-gone"
        assert (
            clear_delta_tables(base_path=tmp_path, table_path=gone, dry_run=False) == 0
        )


class TestDeltaReader:
    def test_resolve_path_variants(self, tmp_path: Path) -> None:
        reader = DeltaReader(tmp_path, NoOpLogger())
        dotted = reader._resolve_path("chembl.activity")
        assert dotted == tmp_path / "chembl" / "activity"
        nested = reader._resolve_path("chembl/activity")
        assert nested == tmp_path / "chembl" / "activity"
        absolute = reader._resolve_path(str(tmp_path / "abs"))
        assert Path(absolute) == tmp_path / "abs"

    async def test_table_exists_and_missing_reads(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reader = DeltaReader(tmp_path, NoOpLogger())
        assert await reader.table_exists("chembl/activity") is False
        table_dir = tmp_path / "chembl" / "activity"
        (table_dir / "_delta_log").mkdir(parents=True)

        def _missing(_path: str) -> object:
            raise DeltaTableNotFoundError("missing")

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta_reader.DeltaTable",
            _missing,
        )
        assert await reader.table_exists("chembl/activity") is False
        with pytest.raises(FileNotFoundError, match="Delta table not found"):
            await reader.read_table("chembl/activity")
        with pytest.raises(FileNotFoundError, match="Delta table not found"):
            await reader.get_schema("chembl/activity")
        with pytest.raises(FileNotFoundError, match="Delta table not found"):
            await reader.get_row_count("chembl/activity")
        with pytest.raises(FileNotFoundError, match="No read candidates"):
            await reader.read_with_fallback("activity", [])
        with pytest.raises(FileNotFoundError, match="Delta table not found"):
            await reader.read_with_fallback("activity", ["1.0.0"])
        await reader.aclose()

    async def test_read_table_limit_and_schema_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        expected = pa.table({"id": ["1"]})
        schema = pa.schema([("id", pa.string())])

        class _Scanner:
            def head(self, limit: int) -> pa.Table:
                assert limit == 1
                return expected

            def to_table(self) -> pa.Table:
                return expected

        class _Dataset:
            def scanner(self, columns: list[str] | None = None) -> _Scanner:
                return _Scanner()

        class _Table:
            def to_pyarrow_dataset(self) -> _Dataset:
                return _Dataset()

            def schema(self) -> object:
                return SimpleNamespace(to_arrow=lambda: schema)

            def count(self) -> int:
                return 1

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta_reader.DeltaTable",
            lambda _path: _Table(),
        )
        (tmp_path / "chembl" / "activity" / "_delta_log").mkdir(parents=True)
        reader = DeltaReader(tmp_path, NoOpLogger())
        limited = await reader.read_table("chembl/activity", limit=1)
        assert expected.equals(limited)
        resolved_schema = await reader.get_schema("chembl/activity")
        assert resolved_schema.names == ["id"]
        assert await reader.get_row_count("chembl/activity") == 1
        assert await reader.table_exists("chembl/activity") is True
        versioned = await reader.read_versioned_table("activity", "1.0.0", limit=1)
        assert expected.equals(versioned)


class TestDeltaReaderHelpers:
    def test_native_count_and_fallback(self, tmp_path: Path) -> None:
        assert try_native_delta_row_count(SimpleNamespace()) is None

        class _BadCount:
            def count(self) -> int:
                raise DeltaError("nope")

        assert try_native_delta_row_count(_BadCount()) is None

        class _GoodCount:
            def count(self) -> int:
                return 7

        assert try_native_delta_row_count(_GoodCount()) == 7

        class _FailingNative:
            def count(self) -> int:
                raise RuntimeError("broken")

        class _Fresh:
            def to_pyarrow_table(self, columns: list[str] | None = None) -> pa.Table:
                return pa.table({"id": ["a", "b"]})

        assert (
            count_delta_rows(
                _FailingNative(),
                tmp_path,
                delta_table_factory=lambda _path: _Fresh(),
            )
            == 2
        )
        assert count_delta_rows(_GoodCount(), tmp_path, delta_table_factory=lambda _p: _Fresh()) == 7


class TestRetentionDedup:
    def test_timeouts_and_identity_helpers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(dedup.platform, "system", lambda: "Windows")
        assert (
            dedup.resolve_test_mode_deduplication_timeout_seconds()
            == dedup.WINDOWS_TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
        )
        monkeypatch.setattr(dedup.platform, "system", lambda: "Linux")
        assert (
            dedup.resolve_test_mode_deduplication_timeout_seconds()
            == dedup.TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.support.retention_dedup.get_settings",
            lambda: SimpleNamespace(test_mode=True, silver_dedup_timeout_seconds=60.0),
        )
        assert dedup.resolve_deduplication_timeout_seconds() == (
            dedup.TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.support.retention_dedup.get_settings",
            lambda: SimpleNamespace(test_mode=False, silver_dedup_timeout_seconds=12.5),
        )
        assert dedup.resolve_deduplication_timeout_seconds() == 12.5
        assert dedup.primary_key_tuple({"id": "1", "k": "x"}, ("id",)) == ("1",)
        none_key = dedup.primary_key_sort_key((None, "a"))
        present_key = dedup.primary_key_sort_key(("a",))
        assert none_key < present_key
        assert dedup.content_identity({"content_hash": "abc"}) == "abc"
        assert dedup.content_identity({"id": "1"}) != ""

    def test_deduplicate_missing_and_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "deltalake.DeltaTable",
            lambda _path: (_ for _ in ()).throw(DeltaTableNotFoundError("missing")),
        )
        with pytest.raises(TableNotFoundError):
            dedup.deduplicate_delta_rows("/missing", ("id",))

        class _Scanner:
            def head(self, _limit: int) -> pa.Table:
                return pa.table({"id": []})

        class _Dataset:
            def scanner(self) -> _Scanner:
                return _Scanner()

        class _Empty:
            def to_pyarrow_dataset(self) -> _Dataset:
                return _Dataset()

            def schema(self) -> object:
                return SimpleNamespace(to_arrow=lambda: pa.schema([("id", pa.string())]))

        monkeypatch.setattr("deltalake.DeltaTable", lambda _path: _Empty())
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.support.retention_dedup.try_native_delta_row_count",
            lambda _dt: 0,
        )
        assert dedup.deduplicate_delta_rows("/empty", ("id",)) == 0

    def test_deduplicate_duplicates_and_conflict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rows = pa.table(
            {
                "id": ["1", "1", "2"],
                "content_hash": ["a", "a", "b"],
            }
        )

        class _Scanner:
            def head(self, _limit: int) -> pa.Table:
                return rows

        class _Dataset:
            def scanner(self) -> _Scanner:
                return _Scanner()

        class _Table:
            def to_pyarrow_dataset(self) -> _Dataset:
                return _Dataset()

            def schema(self) -> object:
                return SimpleNamespace(
                    to_arrow=lambda: pa.schema(
                        [("id", pa.string()), ("content_hash", pa.string())]
                    )
                )

        monkeypatch.setattr("deltalake.DeltaTable", lambda _path: _Table())
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.support.retention_dedup.try_native_delta_row_count",
            lambda _dt: 3,
        )
        writes: list[object] = []

        def _write(**kwargs: object) -> None:
            writes.append(kwargs)

        monkeypatch.setattr("deltalake.write_deltalake", _write)
        removed = dedup.deduplicate_delta_rows("/t", ("id",))
        assert removed == 1
        assert writes

        def _conflict(**_kwargs: object) -> None:
            raise CommitFailedError("busy")

        monkeypatch.setattr("deltalake.write_deltalake", _conflict)
        with pytest.raises(DeltaWriteConflictError):
            dedup.deduplicate_delta_rows("/t", ("id",))
