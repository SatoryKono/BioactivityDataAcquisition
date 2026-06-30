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


def test_windows_e2e_timeout_exceeds_inner_merge_budget() -> None:
    """Windows pytest timeout must exceed the inner Delta merge timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="win32")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="win32"
    )

    assert outer_timeout > inner_timeout
    assert inner_timeout == 180


def test_windows_two_pipeline_timeout_exceeds_single_run_budget() -> None:
    """Sequential multi-pipeline E2E must outlive one full Silver write envelope."""
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="win32"
    )
    two_pipeline_timeout = (
        e2e_conftest._resolve_e2e_sequential_pipeline_timeout_seconds(
            pipeline_count=2,
            platform="win32",
        )
    )

    assert two_pipeline_timeout > inner_timeout
    assert two_pipeline_timeout == 540


def test_exported_two_pipeline_timeout_matches_resolver() -> None:
    """Exported timeout constant should follow the active platform resolver."""
    assert (
        e2e_conftest.E2E_TWO_SEQUENTIAL_PIPELINE_TIMEOUT
        == e2e_conftest._resolve_e2e_sequential_pipeline_timeout_seconds(
            pipeline_count=2
        )
    )


def test_linux_two_pipeline_timeout_exceeds_default_single_run_budget() -> None:
    """Linux sequential multi-pipeline timeout should scale with pipeline count."""
    default_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="linux")
    two_pipeline_timeout = (
        e2e_conftest._resolve_e2e_sequential_pipeline_timeout_seconds(
            pipeline_count=2,
            platform="linux",
        )
    )

    assert two_pipeline_timeout > default_timeout
    assert two_pipeline_timeout == 360


def test_windows_pipeline_matrix_timeout_stays_between_inner_and_outer() -> None:
    """Windows matrix timeout must not preempt the governed Silver timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="win32")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="win32"
    )
    matrix_timeout = (
        e2e_conftest._resolve_e2e_pipeline_matrix_execution_timeout_seconds(
            platform="win32",
            env={},
        )
    )

    assert outer_timeout > matrix_timeout > inner_timeout
    assert matrix_timeout == pytest.approx(240.0)


def test_windows_e2e_plain_delta_writes_are_process_isolated() -> None:
    """Windows E2E plain Delta writes use process isolation for bounded timeouts."""
    assert (
        e2e_conftest._resolve_e2e_plain_write_process_isolation(platform="win32")
        is True
    )


def test_windows_e2e_temp_root_prefers_local_appdata_temp(tmp_path: Path) -> None:
    """Windows E2E sandboxes should prefer a local temp root over TMP/TEMP."""
    local_appdata = tmp_path / "local_appdata"
    local_temp = local_appdata / "Temp"
    local_temp.mkdir(parents=True)
    fallback = tmp_path / "slow_temp"
    fallback.mkdir()

    resolved = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        fallback_tmp=str(fallback),
        env={"LOCALAPPDATA": str(local_appdata)},
    )

    assert resolved == local_temp


def test_windows_e2e_temp_root_honors_explicit_override(tmp_path: Path) -> None:
    """Operators may force an explicit sandbox root when diagnosing I/O issues."""
    override = tmp_path / "override_temp"
    override.mkdir()

    resolved = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        fallback_tmp=str(tmp_path / "fallback"),
        env={"BIOETL_E2E_TEMP_ROOT": str(override)},
    )

    assert resolved == override


def test_windows_e2e_temp_root_falls_back_without_local_appdata(tmp_path: Path) -> None:
    """Windows E2E uses the process tempdir when no local-app-data temp exists."""
    fallback = tmp_path / "fallback_temp"
    fallback.mkdir()

    resolved = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        fallback_tmp=str(fallback),
        env={},
    )

    assert resolved == fallback


def test_non_windows_e2e_timeout_exceeds_inner_merge_budget() -> None:
    """Non-Windows pytest timeout must also exceed the inner Delta merge timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="linux")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="linux"
    )

    assert outer_timeout > inner_timeout
    assert outer_timeout == 120
    assert inner_timeout == 90


def test_non_windows_pipeline_matrix_timeout_stays_between_inner_and_outer() -> None:
    """Non-Windows matrix timeout keeps the existing 105s default contract."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="linux")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="linux"
    )
    matrix_timeout = (
        e2e_conftest._resolve_e2e_pipeline_matrix_execution_timeout_seconds(
            platform="linux",
            env={},
        )
    )

    assert outer_timeout > matrix_timeout > inner_timeout
    assert matrix_timeout == pytest.approx(105.0)


def test_non_windows_e2e_plain_delta_writes_stay_in_process() -> None:
    """Non-Windows E2E keeps the faster in-process Delta write default."""
    assert (
        e2e_conftest._resolve_e2e_plain_write_process_isolation(platform="linux")
        is False
    )


def test_pipeline_matrix_timeout_env_override_is_honored() -> None:
    """The matrix-specific timeout remains explicitly overrideable."""
    matrix_timeout = (
        e2e_conftest._resolve_e2e_pipeline_matrix_execution_timeout_seconds(
            platform="win32",
            env={"BIOETL_E2E_PIPELINE_MATRIX_EXECUTION_TIMEOUT_SECONDS": "123.5"},
        )
    )

    assert matrix_timeout == pytest.approx(123.5)


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
        env={},  # Keep the assertion independent from host LOCALAPPDATA.
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
