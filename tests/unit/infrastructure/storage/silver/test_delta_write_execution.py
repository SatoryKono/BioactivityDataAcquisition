# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for low-level Silver Delta blocking-call execution helpers."""

from __future__ import annotations

import json
import subprocess
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
    _evolve_delta_schema_with_empty_append,
    _run_plain_delta_write_subprocess,
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
    release = threading.Event()
    finished = threading.Event()

    def _blocking_write(**_kwargs: object) -> None:
        try:
            release.wait()
        finally:
            finished.set()

    module = SimpleNamespace(write_deltalake=_blocking_write)

    try:
        with pytest.raises(TimeoutError, match=r"Delta write timed out after 0\.01s"):
            await _write_plain_delta_request(
                load_module=lambda: module,
                request=request,
                mode="append",
                timeout_seconds=0.01,
            )

        assert not finished.is_set()
    finally:
        release.set()


@pytest.mark.asyncio
async def test_inline_plain_write_does_not_fail_after_successful_slow_write() -> None:
    """Completed inline writes must not be rewritten as TimeoutError.

    Regression: GDrive/network mounts often exceed the budget wall-clock while
    still committing durable Delta data. Failing after success aborts workflows
    with partially-written tables (chembl_baseline silver assay path).
    """
    request = _make_request()
    calls: list[dict[str, object]] = []

    def _slow_write(**kwargs: object) -> None:
        time.sleep(0.05)
        calls.append(dict(kwargs))

    module = SimpleNamespace(
        __name__="bioetl.infrastructure.storage.silver_writer",
        write_deltalake=_slow_write,
    )

    await _write_plain_delta_request(
        load_module=lambda: module,
        request=request,
        mode="append",
        timeout_seconds=0.01,
    )

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_local_schema_evolution_reuses_inline_plain_write_path() -> None:
    """Local pre-evolution must not move delta-rs onto a second worker thread."""
    request = _make_request()
    caller_thread = threading.get_ident()
    calls: list[tuple[int, dict[str, object]]] = []

    def _write(**kwargs: object) -> None:
        calls.append((threading.get_ident(), dict(kwargs)))

    module = SimpleNamespace(
        __name__="bioetl.infrastructure.storage.silver_writer",
        write_deltalake=_write,
    )

    evolved_request = await _evolve_delta_schema_with_empty_append(
        load_module=lambda: module,
        request=request,
    )

    assert len(calls) == 1
    worker_thread, kwargs = calls[0]
    assert worker_thread == caller_thread
    assert kwargs["mode"] == "append"
    assert kwargs["schema_mode"] == "merge"
    assert len(kwargs["data"]) == 0
    assert evolved_request.merge_schema is False


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


def test_run_plain_delta_write_subprocess_uses_arrow_file_not_stdin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Large Arrow payloads must not be piped through stdin on Windows."""
    table_path = tmp_path / "silver" / "entity" / "table"
    request = _make_request(str(table_path))
    captured: dict[str, object] = {}

    def _fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        captured["kwargs"] = kwargs
        metadata = json.loads(cmd[3])
        arrow_path = Path(str(metadata["arrow_path"]))
        assert arrow_path.exists()
        assert arrow_path.stat().st_size > 0
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _run_plain_delta_write_subprocess(
        kwargs={
            "table_or_uri": normalize_delta_filesystem_path(request.table_path),
            "mode": "append",
        },
        arrow_data=request.arrow_data,
        timeout_seconds=3.0,
    )

    subprocess_kwargs = captured["kwargs"]
    assert isinstance(subprocess_kwargs, dict)
    assert "input" not in subprocess_kwargs
    assert not any(
        path.exists() for path in table_path.parent.glob(".plain_delta_payload_*.arrow")
    )


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
