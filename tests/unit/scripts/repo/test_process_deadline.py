"""Owned checks must stop descendants, including after a successful parent."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time

import pytest

from scripts.engineering.repo import process_deadline as runner

pytestmark = pytest.mark.unit


def test_inherited_stalled_protocol_pipe_cannot_block_watchdog(tmp_path):
    read_fd, write_fd = os.pipe()
    try:
        with os.fdopen(read_fd, "rb") as stream:
            result = runner.run_owned(
                [sys.executable, "-c", "import sys; sys.stdin.buffer.read(1)"],
                cwd=tmp_path, state_dir=tmp_path, timeout=0.5,
                input_stream=stream,
            )
        assert result.status == "ERROR"
        assert result.reason == "timeout"
        assert result.duration_seconds < 8
    finally:
        os.close(write_fd)


def _run(
    tmp_path: Path, code: str, *, timeout: float = 5, data: bytes = b""
) -> runner.ProcessResult:
    return runner.run_owned(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        state_dir=tmp_path,
        timeout=timeout,
        input_bytes=data,
    )


def _alive(pid: int) -> bool:
    if os.name == "nt":
        from ctypes import wintypes as w

        api = runner._windows_api()
        api.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        api.WaitForSingleObject.restype = w.DWORD
        handle = api.OpenProcess(0x00101000, False, pid)
        if not handle:
            return False
        try:
            return api.WaitForSingleObject(handle, 0) == 0x00000102
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")
    return not stat.exists() or stat.read_text().split(")", 1)[1].split()[0] != "Z"


def _assert_stopped(pid: int) -> None:
    deadline = time.monotonic() + 2
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not _alive(pid), "owned descendant remained alive after cleanup"


def test_literal_command_receives_exact_input_without_output_leak(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        "import sys; assert sys.stdin.buffer.read() == b'fixture-input'; "
        "print('private-child-output'); sys.stderr.write('private-child-error')",
        data=b"fixture-input",
    )
    assert result.status == "PASS"
    assert result.returncode == 0
    assert "private-child" not in json.dumps(asdict(result))


def test_nonzero_and_missing_command_are_not_pass(tmp_path: Path) -> None:
    failed = _run(tmp_path, "raise SystemExit(7)")
    assert failed.status == "FAIL"
    assert failed.returncode == 7
    missing = runner.run_owned(
        [str(tmp_path / "absent-executable")],
        cwd=tmp_path,
        state_dir=tmp_path,
        timeout=2,
    )
    assert missing.status == "ERROR"
    assert missing.reason == "execution_unavailable"


@pytest.mark.parametrize("parent_sleeps", [True, False])
@pytest.mark.parametrize("detached", [False, True])
def test_descendant_is_stopped_on_timeout_and_normal_parent_exit(
    tmp_path: Path, parent_sleeps: bool, detached: bool
) -> None:
    if os.name == "nt" and detached:
        pytest.skip("setsid is POSIX-specific; Windows descendants use a job")
    pid_file = tmp_path / "child.pid"
    code = (
        "import subprocess,sys,time; from pathlib import Path; "
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
        f"start_new_session={detached!r}); "
        f"Path({str(pid_file)!r}).write_text(str(child.pid)); "
        + ("time.sleep(60)" if parent_sleeps else "raise SystemExit(0)")
    )
    result = _run(tmp_path, code, timeout=2)
    assert pid_file.exists(), "fixture parent did not start before its deadline"
    assert result.status == ("ERROR" if parent_sleeps else "PASS")
    assert result.reason == ("timeout" if parent_sleeps else "completed")
    _assert_stopped(int(pid_file.read_text()))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 901, True])
def test_invalid_deadline_cannot_launch(tmp_path: Path, timeout: float) -> None:
    result = _run(tmp_path, "raise AssertionError('must not launch')", timeout=timeout)
    assert result.status == "ERROR"
    assert result.reason == "invalid_deadline"


def test_oversized_input_cannot_launch(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "raise AssertionError('must not launch')",
        data=b"x" * (8 * 1024 * 1024 + 1),
    )
    assert result.status == "ERROR"
    assert result.reason == "input_too_large"


def test_user_interrupt_is_propagated_after_child_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "interrupt-child.pid"
    original = runner._await_exit

    def interrupt(*args: object) -> bool:
        deadline = time.monotonic() + 2
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        monkeypatch.setattr(runner, "_await_exit", original)
        raise KeyboardInterrupt

    monkeypatch.setattr(runner, "_await_exit", interrupt)
    with pytest.raises(KeyboardInterrupt):
        _run(
            tmp_path,
            "import subprocess,sys,time;from pathlib import Path;"
            "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
            f"start_new_session={os.name != 'nt'!r});"
            f"Path({str(pid_file)!r}).write_text(str(child.pid));time.sleep(60)",
        )
    assert pid_file.exists()
    _assert_stopped(int(pid_file.read_text()))


def test_parallel_invocations_do_not_share_input_files(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def invoke(value: int) -> runner.ProcessResult:
        payload = str(value).encode()
        return _run(
            tmp_path,
            f"import sys;assert sys.stdin.buffer.read()=={payload!r}",
            data=payload,
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(invoke, range(6)))
    assert all(result.status == "PASS" for result in results)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "raw",
    [
        b"private-invalid-json",
        b"{}",
        b'{"reason":"completed","returncode":0,"cleaned":false}',
        b'{"reason":"completed","returncode":null,"cleaned":true}',
        b'{"reason":"completed","returncode":true,"cleaned":true}',
        b'{"reason":"private-unqualified-reason","returncode":0,"cleaned":true}',
    ],
)
def test_missing_or_invalid_supervisor_evidence_cannot_pass(raw: bytes) -> None:
    start = time.monotonic()
    result = runner._supervisor_result(raw, start, start + 10, False)
    assert result.status == "ERROR"
    assert "private" not in json.dumps(asdict(result))


def test_late_supervisor_result_is_timeout_even_after_zero_exit() -> None:
    start = time.monotonic()
    raw = b'{"reason":"completed","returncode":0,"cleaned":true}'
    result = runner._supervisor_result(raw, start, start + 10, True)
    assert result.status == "ERROR"
    assert result.reason == "timeout"
