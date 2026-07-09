"""Unit tests for low-level Silver Delta blocking-call execution helpers."""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
)
from bioetl.infrastructure.storage.silver import delta_write_execution as subject
from bioetl.infrastructure.storage.silver.delta_request_models import (
    _DeltaWriteRequest,
)
from bioetl.infrastructure.storage.silver.delta_write_execution import (
    _await_blocking_deltalake_call,
    _write_plain_delta_request,
)

pytestmark = pytest.mark.unit

_DEFAULT_TABLE_PATH = str(
    Path(tempfile.gettempdir())
    / "bioetl-delta-write-execution"
    / "silver"
    / "test"
    / "table"
)


def _make_request(table_path: str = _DEFAULT_TABLE_PATH) -> _DeltaWriteRequest:
    """Build a minimal Delta write request for timeout-path tests."""
    return _DeltaWriteRequest(
        validated_mode=SilverWriteMode.APPEND,
        table_path=table_path,
        arrow_data=pa.table({"id": [1], "value": ["x"]}),
        primary_keys=["id"],
        partition_cols=None,
    )


@pytest.mark.asyncio
async def test_await_blocking_deltalake_call_returns_result() -> None:
    """Successful blocking calls should resolve through the daemon-thread bridge."""
    result = await _await_blocking_deltalake_call(
        operation_name="unit-success",
        call=lambda: "ok",
    )

    assert result == "ok"


@pytest.mark.asyncio
async def test_write_plain_delta_request_times_out_promptly_without_executor_join() -> (
    None
):
    """Plain writes should surface timeout without waiting for a stuck native thread."""
    request = _make_request()
    release_after_seconds = 2.0
    release = threading.Event()
    finished = threading.Event()

    def _blocking_write(**_kwargs: object) -> None:
        try:
            release.wait(timeout=release_after_seconds)
        finally:
            finished.set()

    module = SimpleNamespace(write_deltalake=_blocking_write)
    release_timer = threading.Timer(release_after_seconds, release.set)
    release_timer.daemon = True
    release_timer.start()

    started = time.perf_counter()
    try:
        with pytest.raises(TimeoutError, match=r"Delta write timed out after 0\.01s"):
            await _write_plain_delta_request(
                load_module=lambda: module,
                request=request,
                mode="append",
                timeout_seconds=0.01,
            )
        elapsed = time.perf_counter() - started

        assert elapsed < release_after_seconds / 2
        assert not finished.is_set()
    finally:
        release.set()
        release_timer.cancel()


@pytest.mark.asyncio
async def test_write_plain_delta_request_can_use_process_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Process isolation should bypass in-process delta-rs calls when enabled."""
    request = _make_request()
    calls: list[tuple[dict[str, object], pa.Table, float]] = []

    def _fake_subprocess_write(
        *,
        kwargs: dict[str, object],
        arrow_data: pa.Table,
        timeout_seconds: float,
    ) -> None:
        calls.append((kwargs, arrow_data, timeout_seconds))

    module = SimpleNamespace(
        write_deltalake=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("in-process write must not run")
        ),
    )
    monkeypatch.setattr(
        subject,
        "_run_plain_delta_write_subprocess",
        _fake_subprocess_write,
    )

    await _write_plain_delta_request(
        load_module=lambda: module,
        request=request,
        mode="append",
        timeout_seconds=3.0,
        process_isolation=True,
    )

    assert len(calls) == 1
    kwargs, arrow_data, timeout_seconds = calls[0]
    assert kwargs["table_or_uri"] == normalize_delta_filesystem_path(request.table_path)
    assert kwargs["mode"] == "append"
    assert "partition_by" not in kwargs
    assert arrow_data is request.arrow_data
    assert timeout_seconds == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_await_blocking_deltalake_call_propagates_exceptions() -> None:
    """Exceptions raised inside the blocking call should reach the awaiter."""

    def _raise() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await _await_blocking_deltalake_call(
            operation_name="unit-error",
            call=_raise,
        )
