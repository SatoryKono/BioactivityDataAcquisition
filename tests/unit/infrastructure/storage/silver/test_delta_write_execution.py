"""Unit tests for low-level Silver Delta blocking-call execution helpers."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.delta_request_models import (
    _DeltaWriteRequest,
)
from bioetl.infrastructure.storage.silver.delta_write_execution import (
    _await_blocking_deltalake_call,
    _write_plain_delta_request,
)

pytestmark = pytest.mark.unit


def _make_request(table_path: str = "silver/test/table") -> _DeltaWriteRequest:
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
    module = SimpleNamespace(
        write_deltalake=lambda **_kwargs: time.sleep(0.2),
    )

    started = time.perf_counter()
    with pytest.raises(TimeoutError, match="Delta write timed out after 0.01s"):
        await _write_plain_delta_request(
            load_module=lambda: module,
            request=request,
            mode="append",
            timeout_seconds=0.01,
        )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.15


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
