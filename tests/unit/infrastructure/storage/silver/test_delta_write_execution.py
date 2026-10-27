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

import asyncio
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import psutil
import pyarrow as pa
import pytest

from bioetl.domain.locking import (
    register_lock_release_barrier,
    reset_lock_release_barriers,
    wait_lock_release_barriers,
)
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
        await wait_lock_release_barriers()


@pytest.mark.asyncio
async def test_unarmed_lock_context_does_not_join_timed_out_worker() -> None:
    """Without a lock hold, a timeout must not wait for the blocked worker."""
    await wait_lock_release_barriers()
    called = False

    async def _barrier() -> None:
        nonlocal called
        called = True

    register_lock_release_barrier(_barrier)
    await wait_lock_release_barriers()
    assert called is False


@pytest.mark.asyncio
async def test_timed_out_delta_write_is_joined_by_lock_release_barrier() -> None:
    """Lock release must wait until a timed-out Delta worker finishes."""
    request = _make_request()
    release = threading.Event()
    finished = threading.Event()

    def _blocking_write(**_kwargs: object) -> None:
        try:
            release.wait(timeout=5)
        finally:
            finished.set()

    module = SimpleNamespace(write_deltalake=_blocking_write)
    reset_lock_release_barriers()
    waiter: asyncio.Task[None] | None = None
    try:
        with pytest.raises(TimeoutError, match=r"Delta write timed out after 0\.05s"):
            await _write_plain_delta_request(
                load_module=lambda: module,
                request=request,
                mode="append",
                timeout_seconds=0.05,
            )
        assert not finished.is_set()
        waiter = asyncio.create_task(wait_lock_release_barriers())
        await asyncio.sleep(0.05)
        assert not waiter.done()
        release.set()
        await waiter
        assert finished.is_set()
    finally:
        release.set()
        if waiter is not None and not waiter.done():
            await waiter
        await wait_lock_release_barriers()


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
    calls: list[tuple[dict[str, object], pa.Table, float, threading.Event]] = []

    def _fake_subprocess_write(
        *,
        kwargs: dict[str, object],
        arrow_data: pa.Table,
        timeout_seconds: float,
        cancel_event: threading.Event,
    ) -> None:
        calls.append((kwargs, arrow_data, timeout_seconds, cancel_event))

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
    kwargs, arrow_data, timeout_seconds, cancel_event = calls[0]
    assert kwargs["table_or_uri"] == normalize_delta_filesystem_path(request.table_path)
    assert kwargs["mode"] == "append"
    assert "partition_by" not in kwargs
    assert arrow_data is request.arrow_data
    assert timeout_seconds == pytest.approx(3.0)
    assert isinstance(cancel_event, threading.Event)
    assert not cancel_event.is_set()


@pytest.mark.asyncio
async def test_process_isolation_cancellation_signals_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelling the await must set the event the child wait loop polls."""
    request = _make_request()
    started = threading.Event()
    observed: dict[str, threading.Event] = {}

    def _fake_subprocess_write(
        *,
        kwargs: dict[str, object],
        arrow_data: pa.Table,
        timeout_seconds: float,
        cancel_event: threading.Event,
    ) -> None:
        del kwargs, arrow_data, timeout_seconds
        observed["cancel_event"] = cancel_event
        started.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if cancel_event.is_set():
                return
            time.sleep(0.01)
        raise AssertionError("cancel event was not set")

    monkeypatch.setattr(
        subject,
        "_run_plain_delta_write_subprocess",
        _fake_subprocess_write,
    )
    task = asyncio.create_task(
        _write_plain_delta_request(
            load_module=lambda: SimpleNamespace(),
            request=request,
            mode="append",
            timeout_seconds=3.0,
            process_isolation=True,
        )
    )
    assert await asyncio.to_thread(started.wait, 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert observed["cancel_event"].is_set()


def test_run_plain_delta_write_subprocess_bounded_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Oversized continuous output to both streams must be bounded without hanging."""
    table_path = tmp_path / "silver" / "entity" / "table"
    request = _make_request(str(table_path))

    script = """
import sys
for _ in range(1000):
    sys.stdout.write("x" * 100 + "\\n")
    sys.stderr.write("y" * 100 + "\\n")
sys.stdout.flush()
sys.stderr.flush()
sys.stdout.write("stdout_tail")
sys.stderr.write("stderr_tail")
sys.exit(1)
"""
    # Replace the execution code with our spam script
    monkeypatch.setattr(subject, "_PLAIN_DELTA_WRITE_SUBPROCESS_CODE", script)

    with pytest.raises(RuntimeError) as exc_info:
        _run_plain_delta_write_subprocess(
            kwargs={
                "table_or_uri": normalize_delta_filesystem_path(request.table_path),
                "mode": "append",
            },
            arrow_data=request.arrow_data,
            timeout_seconds=5.0,
        )

    msg = str(exc_info.value)
    assert "exit_code=1" in msg
    assert "stdout_tail" in msg
    assert "stderr_tail" in msg
    assert len(msg) < 10000  # Ensure we didn't accumulate unbounded output


def test_run_plain_delta_write_subprocess_timeout_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Timeout must clean up the child process and pipes without leaking."""
    table_path = tmp_path / "silver" / "entity" / "table"
    request = _make_request(str(table_path))
    pid_path = tmp_path / "child.pid"

    script = f"""
import os
import sys
import time
from pathlib import Path
Path({str(pid_path)!r}).write_text(str(os.getpid()), encoding="utf-8")
sys.stdout.write("started\\n")
sys.stdout.flush()
time.sleep(10)
"""
    monkeypatch.setattr(subject, "_PLAIN_DELTA_WRITE_SUBPROCESS_CODE", script)

    start_time = time.monotonic()
    with pytest.raises(TimeoutError):
        _run_plain_delta_write_subprocess(
            kwargs={
                "table_or_uri": normalize_delta_filesystem_path(request.table_path),
                "mode": "append",
            },
            arrow_data=request.arrow_data,
            timeout_seconds=0.1,
        )
    elapsed = time.monotonic() - start_time
    assert elapsed < 1.0
    pid = int(pid_path.read_text(encoding="utf-8"))
    assert not psutil.pid_exists(pid)


def test_run_plain_delta_write_subprocess_cancel_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cancellation must kill the child without waiting out the full timeout."""
    table_path = tmp_path / "silver" / "entity" / "table"
    request = _make_request(str(table_path))
    pid_path = tmp_path / "child.pid"
    script = f"""
import os
import sys
import time
from pathlib import Path
Path({str(pid_path)!r}).write_text(str(os.getpid()), encoding="utf-8")
time.sleep(30)
"""
    monkeypatch.setattr(subject, "_PLAIN_DELTA_WRITE_SUBPROCESS_CODE", script)
    cancel_event = threading.Event()

    def _cancel_when_started() -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not pid_path.exists():
            time.sleep(0.01)
        cancel_event.set()

    threading.Thread(target=_cancel_when_started, daemon=True).start()
    start_time = time.monotonic()
    with pytest.raises(TimeoutError):
        _run_plain_delta_write_subprocess(
            kwargs={
                "table_or_uri": normalize_delta_filesystem_path(request.table_path),
                "mode": "append",
            },
            arrow_data=request.arrow_data,
            timeout_seconds=30.0,
            cancel_event=cancel_event,
        )
    assert time.monotonic() - start_time < 2.0
    pid = int(pid_path.read_text(encoding="utf-8"))
    assert not psutil.pid_exists(pid)


def test_run_plain_delta_write_subprocess_closes_pipes_before_join(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Open pipes must not keep the parent waiting after the child exits."""
    table_path = tmp_path / "silver" / "entity" / "table"
    request = _make_request(str(table_path))

    class _BlockingStream:
        def __init__(self) -> None:
            self._closed = threading.Event()

        def read(self, _size: int) -> bytes:
            if not self._closed.wait(timeout=30):
                raise AssertionError("stream was not closed")
            return b""

        def close(self) -> None:
            self._closed.set()

    class _FakePopen:
        def __init__(self, cmd: list[str], **kwargs: object) -> None:
            metadata = json.loads(cmd[3])
            assert Path(str(metadata["arrow_path"])).exists()
            self.stdout = _BlockingStream()
            self.stderr = _BlockingStream()
            self.returncode = 0
            self.args: list[str] = cmd

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

        def kill(self) -> None:
            self.returncode = -9

    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    start_time = time.monotonic()
    _run_plain_delta_write_subprocess(
        kwargs={
            "table_or_uri": normalize_delta_filesystem_path(request.table_path),
            "mode": "append",
        },
        arrow_data=request.arrow_data,
        timeout_seconds=5.0,
    )
    assert time.monotonic() - start_time < 1.5


def test_run_plain_delta_write_subprocess_uses_arrow_file_not_stdin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Large Arrow payloads must not be piped through stdin on Windows."""
    table_path = tmp_path / "silver" / "entity" / "table"
    request = _make_request(str(table_path))
    captured: dict[str, object] = {}

    class _FakePopen:
        def __init__(self, cmd: list[str], **kwargs: object) -> None:
            captured["kwargs"] = kwargs
            metadata = json.loads(cmd[3])
            arrow_path = Path(str(metadata["arrow_path"]))
            assert arrow_path.exists()
            assert arrow_path.stat().st_size > 0
            import io

            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(b"")
            self.returncode = 0

        def wait(self, timeout=None):
            pass

        def kill(self):
            pass

    monkeypatch.setattr(subprocess, "Popen", _FakePopen)

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
