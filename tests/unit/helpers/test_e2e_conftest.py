"""Unit tests for E2E conftest Delta helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tests.e2e import conftest as e2e_conftest

pytestmark = pytest.mark.unit


def test_read_delta_records_uses_shared_delta_reader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sentinel_table = object()
    observed: dict[str, object] = {}
    expected = [{"entity_id": "row-1"}]

    def _fake_load_delta_table() -> object:
        def _factory(path: str) -> object:
            observed["path"] = path
            return sentinel_table

        return _factory

    def _fake_load_delta_record_reader() -> object:
        def _reader(
            table: object, columns: list[str] | None = None
        ) -> list[dict[str, str]]:
            observed["table"] = table
            observed["columns"] = columns
            return expected

        return _reader

    monkeypatch.setattr(e2e_conftest, "_load_delta_table", _fake_load_delta_table)
    monkeypatch.setattr(
        e2e_conftest,
        "_load_delta_record_reader",
        _fake_load_delta_record_reader,
    )
    monkeypatch.setattr(
        e2e_conftest,
        "_prefer_active_parquet_delta_reads",
        lambda: False,
    )

    result = asyncio.run(
        e2e_conftest._read_delta_records(tmp_path / "silver" / "chembl_activity")
    )

    assert result == expected
    assert observed == {
        "path": str(tmp_path / "silver" / "chembl_activity"),
        "table": sentinel_table,
        "columns": None,
    }


def test_read_delta_records_prefers_active_parquet_reader_on_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed: dict[str, object] = {}
    expected = [{"entity_id": "row-1"}]

    def _fake_load_delta_table() -> object:
        def _factory(path: str) -> object:
            observed["path"] = path
            return object()

        return _factory

    def _unexpected_load_delta_record_reader() -> object:
        raise AssertionError("shared delta reader should not be used on win32 E2E")

    def _fake_read_active_parquet_records_from_delta_log(
        table_path: Path,
        columns: list[str] | None = None,
    ) -> list[dict[str, str]]:
        observed["fallback_path"] = str(table_path)
        observed["columns"] = columns
        return expected

    monkeypatch.setattr(e2e_conftest, "_load_delta_table", _fake_load_delta_table)
    monkeypatch.setattr(
        e2e_conftest,
        "_load_delta_record_reader",
        _unexpected_load_delta_record_reader,
    )
    monkeypatch.setattr(
        e2e_conftest,
        "_read_active_parquet_records_from_delta_log",
        _fake_read_active_parquet_records_from_delta_log,
    )
    monkeypatch.setattr(
        e2e_conftest,
        "_prefer_active_parquet_delta_reads",
        lambda: True,
    )

    result = asyncio.run(
        e2e_conftest._read_delta_records(tmp_path / "silver" / "chembl_activity")
    )

    assert result == expected
    assert observed == {
        "path": str(tmp_path / "silver" / "chembl_activity"),
        "fallback_path": str(tmp_path / "silver" / "chembl_activity"),
        "columns": None,
    }


def test_read_delta_records_timeout_surfaces_harness_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "silver" / "chembl_activity"
    (table_path / "_delta_log").mkdir(parents=True)

    async def _raise_timeout(_awaitable: object, *, timeout: int) -> object:
        raise TimeoutError()

    async def _exercise() -> None:
        loop = asyncio.get_running_loop()

        class _FakeLoop:
            def __init__(self) -> None:
                self._calls = 0

            def run_in_executor(self, _executor: object, func: object) -> asyncio.Future[object]:
                self._calls += 1
                future = loop.create_future()
                if self._calls == 1:
                    return future
                try:
                    future.set_result(func())
                except BaseException as exc:  # pragma: no cover - exercised via tests
                    future.set_exception(exc)
                return future

        monkeypatch.setattr(asyncio, "get_running_loop", lambda: _FakeLoop())
        monkeypatch.setattr(asyncio, "wait_for", _raise_timeout)
        monkeypatch.setattr(
            e2e_conftest,
            "_prefer_active_parquet_delta_reads",
            lambda: False,
        )
        monkeypatch.setattr(
            e2e_conftest,
            "_read_active_parquet_records_from_delta_log",
            lambda _table_path: [],
        )

        with pytest.raises(
            TimeoutError,
            match=(
                "delta_log_present=True; prefer_active_parquet=False. "
                "fallback_status=delta_log_parquet_empty"
            ),
        ):
            await e2e_conftest._read_delta_records(table_path)

    asyncio.run(_exercise())


def test_read_delta_records_uses_delta_log_fallback_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "silver" / "chembl_activity"
    (table_path / "_delta_log").mkdir(parents=True)
    expected = [{"entity_id": "fallback-row"}]

    async def _raise_timeout(_awaitable: object, *, timeout: int) -> object:
        raise TimeoutError()

    async def _exercise() -> None:
        loop = asyncio.get_running_loop()

        class _FakeLoop:
            def __init__(self) -> None:
                self._calls = 0

            def run_in_executor(self, _executor: object, func: object) -> asyncio.Future[object]:
                self._calls += 1
                future = loop.create_future()
                if self._calls == 1:
                    return future
                try:
                    future.set_result(func())
                except BaseException as exc:  # pragma: no cover - exercised via tests
                    future.set_exception(exc)
                return future

        monkeypatch.setattr(asyncio, "get_running_loop", lambda: _FakeLoop())
        monkeypatch.setattr(asyncio, "wait_for", _raise_timeout)
        monkeypatch.setattr(
            e2e_conftest,
            "_prefer_active_parquet_delta_reads",
            lambda: False,
        )
        monkeypatch.setattr(
            e2e_conftest,
            "_read_active_parquet_records_from_delta_log",
            lambda fallback_table_path, columns=None: (
                expected
                if fallback_table_path == table_path and columns is None
                else []
            ),
        )

        result = await e2e_conftest._read_delta_records(table_path)
        assert result == expected

    asyncio.run(_exercise())


def test_read_delta_records_corrupt_delta_log_is_not_timeout_recovered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "silver" / "chembl_activity"
    (table_path / "_delta_log").mkdir(parents=True)

    async def _raise_timeout(_awaitable: object, *, timeout: int) -> object:
        raise TimeoutError()

    async def _exercise() -> None:
        loop = asyncio.get_running_loop()

        class _FakeLoop:
            def __init__(self) -> None:
                self._calls = 0

            def run_in_executor(self, _executor: object, func: object) -> asyncio.Future[object]:
                self._calls += 1
                future = loop.create_future()
                if self._calls == 1:
                    return future
                try:
                    future.set_result(func())
                except BaseException as exc:  # pragma: no cover - exercised via tests
                    future.set_exception(exc)
                return future

        monkeypatch.setattr(asyncio, "get_running_loop", lambda: _FakeLoop())
        monkeypatch.setattr(asyncio, "wait_for", _raise_timeout)
        monkeypatch.setattr(
            e2e_conftest,
            "_prefer_active_parquet_delta_reads",
            lambda: False,
        )

        def _raise_corruption(
            _table_path: Path,
            columns: list[str] | None = None,
        ) -> list[dict[str, str]]:
            del columns
            raise e2e_conftest.E2EDeltaTableCorruptionError(
                "fallback_status=corrupt_delta_log"
            )

        monkeypatch.setattr(
            e2e_conftest,
            "_read_active_parquet_records_from_delta_log",
            _raise_corruption,
        )

        with pytest.raises(
            e2e_conftest.E2EDeltaTableCorruptionError,
            match="corrupt_delta_log",
        ):
            await e2e_conftest._read_delta_records(table_path)

    asyncio.run(_exercise())


@pytest.mark.parametrize(
    ("file_uri", "expected"),
    [
        (
            "file:///E:/tmp/bioetl/table/part-0001.parquet",
            "E:/tmp/bioetl/table/part-0001.parquet",
        ),
        (
            "file:///tmp/bioetl/table/part-0001.parquet",
            "/tmp/bioetl/table/part-0001.parquet",
        ),
        ("/tmp/bioetl/table/part-0001.parquet", "/tmp/bioetl/table/part-0001.parquet"),
    ],
)
def test_resolve_parquet_file_uri_normalizes_local_paths(
    file_uri: str,
    expected: str,
) -> None:
    assert e2e_conftest._resolve_parquet_file_uri(file_uri) == expected


def test_resolve_e2e_temp_root_uses_system_temp_on_windows(tmp_path: Path) -> None:
    posix_tmp = tmp_path / "drive_relative_tmp"
    posix_tmp.mkdir()
    windows_temp = tmp_path / "windows_temp"

    result = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        posix_tmp=posix_tmp,
        fallback_tmp=str(windows_temp),
    )

    assert result == windows_temp


def test_resolve_e2e_temp_root_prefers_posix_tmp_when_available(
    tmp_path: Path,
) -> None:
    posix_tmp = tmp_path / "tmp"
    posix_tmp.mkdir()
    fallback = tmp_path / "fallback"

    result = e2e_conftest._resolve_e2e_temp_root(
        platform="linux",
        posix_tmp=posix_tmp,
        fallback_tmp=str(fallback),
    )

    assert result == posix_tmp


def test_resolve_e2e_temp_root_falls_back_when_posix_tmp_missing(
    tmp_path: Path,
) -> None:
    fallback = tmp_path / "fallback"

    result = e2e_conftest._resolve_e2e_temp_root(
        platform="linux",
        posix_tmp=tmp_path / "missing",
        fallback_tmp=str(fallback),
    )

    assert result == fallback
