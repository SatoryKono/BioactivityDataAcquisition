"""Bound owned check processes and their descendants without logging payloads.

This internal helper runs no installer and provides no filesystem sandbox.
Windows children start suspended until assigned to a kill-on-close job.
Linux uses an isolated subreaper and pidfds for detached descendants. Forced
supervisor/host termination still needs a host boundary; absent cleanup evidence
never qualifies as PASS.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Literal


@dataclass(frozen=True)
class ProcessResult:
    """Only controlled reasons, return codes and measured duration leave here."""

    status: Literal["PASS", "FAIL", "ERROR"]
    reason: str
    returncode: int | None
    duration_seconds: float


def _result(start: float, code: int | None, reason: str) -> ProcessResult:
    status: Literal["PASS", "FAIL", "ERROR"] = "ERROR"
    if reason == "completed":
        status = "PASS" if code == 0 else "FAIL"
    return ProcessResult(status, reason, code, round(time.monotonic() - start, 6))


def run_owned(
    argv: Sequence[str],
    *,
    cwd: Path,
    state_dir: Path,
    timeout: float,
    input_bytes: bytes = b"",
    input_stream: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> ProcessResult:
    """Run a literal argument vector with bounded input and silent child output.

    The caller owns the command and paths. Untrusted child output and command
    arguments are never echoed. File input avoids a blocking pipe write before
    Windows wait timeouts. Temporary inputs are unique across concurrent runs.
    """
    start = time.monotonic()
    if (
        isinstance(argv, (str, bytes))
        or not argv
        or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
    ):
        return _result(start, None, "invalid_command")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
        or timeout > 900
    ):
        return _result(start, None, "invalid_deadline")
    if not isinstance(input_bytes, bytes) or len(input_bytes) > 8 * 1024 * 1024:
        return _result(start, None, "input_too_large")
    if input_stream is not None and input_bytes:
        return _result(start, None, "conflicting_input")
    try:
        if input_stream is not None:
            # Pass an inherited protocol pipe without reading it in the watchdog.
            # The owned child bounds its payload; a stalled writer hits timeout.
            input_stream.fileno()
            return _run_process(
                argv, cwd, input_stream, env, start, start + timeout, state_dir
            )
        with tempfile.TemporaryFile(dir=state_dir) as stream:
            stream.write(input_bytes)
            stream.seek(0)
            return _run_process(
                argv, cwd, stream, env, start, start + timeout, state_dir
            )
    except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
        return _result(start, None, "execution_unavailable")


def _run_process(
    argv: Sequence[str],
    cwd: Path,
    stream: Any,
    env: Mapping[str, str] | None,
    start: float,
    deadline: float,
    state_dir: Path,
) -> ProcessResult:
    if os.name != "nt":
        return _run_supervised(argv, cwd, stream, env, start, deadline, state_dir)
    job = _WindowsJob() if os.name == "nt" else None
    if job is None:
        _require_posix()
    proc: subprocess.Popen[bytes] | None = None
    expired = False
    cleanup_ok = True
    try:
        if time.monotonic() >= deadline:
            return _result(start, None, "timeout")
        options: dict[str, Any] = {"start_new_session": True}
        if job is not None:
            options = {"creationflags": 0x00000004 | 0x08000000}
        proc = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=env,
            stdin=stream,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **options,
        )
        if job is not None:
            job.assign_and_resume(proc.pid)
        expired = not _await_exit(proc, deadline)
    finally:
        if job is not None:
            cleanup_ok = job.close()
        elif proc is not None:
            cleanup_ok = _kill_group(proc.pid)
        if proc is not None:
            # Also covers a suspended Windows child whose job assignment failed.
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
    if not cleanup_ok:
        return _result(start, None, "containment_cleanup_failed")
    assert proc is not None
    late = expired or time.monotonic() > deadline
    return _result(start, proc.returncode, "timeout" if late else "completed")


def _run_supervised(
    argv: Sequence[str],
    cwd: Path,
    stream: Any,
    env: Mapping[str, str] | None,
    start: float,
    deadline: float,
    state_dir: Path,
) -> ProcessResult:
    """A dedicated subreaper cannot adopt another caller thread's processes."""
    _require_posix()
    from scripts.engineering.repo import process_supervisor

    payload = json.dumps(
        {
            "argv": list(argv),
            "cwd": str(cwd),
            "deadline": deadline,
            "parent_pid": os.getpid(),
        }
    ).encode()
    if len(payload) > 1024 * 1024:
        return _result(start, None, "invalid_command")
    entry = (
        "import sys;sys.path.insert(0,sys.argv[1]);"
        f"from {process_supervisor.__name__} import main;"
        "raise SystemExit(main(int(sys.argv[2]),int(sys.argv[3])))"
    )
    with (
        tempfile.TemporaryFile(dir=state_dir) as config,
        tempfile.TemporaryFile(dir=state_dir) as result,
    ):
        config.write(payload)
        config.seek(0)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                entry,
                str(Path(__file__).resolve().parents[3]),
                str(config.fileno()),
                str(result.fileno()),
            ],
            cwd=cwd,
            env=env,
            stdin=stream,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(config.fileno(), result.fileno()),
            start_new_session=True,
        )
        forced = False
        try:
            if not _await_exit(proc, deadline + 6):
                forced = True
                _stop_supervisor(proc)
        except KeyboardInterrupt:
            _stop_supervisor(proc)
            raise
        finally:
            cleanup_ok = _kill_group(proc.pid)
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
        result.seek(0)
        raw = result.read(4097)
    if not cleanup_ok or proc.returncode != 0:
        return _result(start, None, "supervisor_failure")
    return _supervisor_result(raw, start, deadline, forced)


def _stop_supervisor(proc: subprocess.Popen[bytes]) -> None:
    """Request cleanup before the outer watchdog terminates a stuck supervisor."""
    try:
        os.kill(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    _await_exit(proc, time.monotonic() + 5)


def _supervisor_result(
    raw: bytes, start: float, deadline: float, forced: bool
) -> ProcessResult:
    """Only an explicit empty-tree receipt can qualify a command result."""
    try:
        data = json.loads(raw) if len(raw) <= 4096 else None
        if not isinstance(data, dict) or data.get("cleaned") is not True:
            raise ValueError("missing cleanup proof")
        reason, code = data["reason"], data["returncode"]
        allowed = {
            "completed",
            "timeout",
            "parent_stopped",
            "execution_unavailable",
            "containment_unavailable",
            "invalid_request",
            "supervisor_failure",
        }
        if reason not in allowed or (
            code is not None and (not isinstance(code, int) or isinstance(code, bool))
        ):
            raise ValueError("invalid supervisor result")
        if reason == "completed" and code is None:
            raise ValueError("missing exit evidence")
    except (ValueError, TypeError, KeyError):
        return _result(start, None, "supervisor_evidence_unavailable")
    if forced or time.monotonic() > deadline:
        return _result(start, code, "timeout")
    return _result(start, code, reason)


def _await_exit(proc: subprocess.Popen[bytes], deadline: float) -> bool:
    """Wait without losing POSIX group identity to PID reuse before cleanup."""
    if os.name == "nt":
        try:
            proc.wait(timeout=max(0, deadline - time.monotonic()))
            return True
        except subprocess.TimeoutExpired:
            return False
    api = _require_posix()
    flags = api["WEXITED"] | api["WNOHANG"] | api["WNOWAIT"]
    while time.monotonic() < deadline:
        if api["waitid"](api["P_PID"], proc.pid, flags):
            return True
        time.sleep(min(0.02, max(0, deadline - time.monotonic())))
    return False


def _require_posix() -> dict[str, Any]:
    required = ("waitid", "WNOWAIT", "WEXITED", "WNOHANG", "P_PID", "killpg")
    api = {name: getattr(os, name, None) for name in required}
    api["SIGKILL"] = getattr(signal, "SIGKILL", None)
    if any(value is None for value in api.values()):
        raise OSError("waitable process-group identity is unavailable")
    return api


def _kill_group(pid: int) -> bool:
    """Only the group created by this helper is a termination target."""
    try:
        api = _require_posix()
        api["killpg"](pid, api["SIGKILL"])
    except ProcessLookupError:
        pass
    except OSError:
        return False
    return True


def _windows_api() -> Any:
    """Declare documented kernel32 signatures before passing 64-bit handles."""
    import ctypes
    from ctypes import wintypes as w

    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise OSError("Windows job API unavailable")
    api = loader("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([w.LPVOID, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": (
            [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD],
            w.BOOL,
        ),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
        "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "CreateToolhelp32Snapshot": ([w.DWORD, w.DWORD], w.HANDLE),
        "Thread32First": ([w.HANDLE, w.LPVOID], w.BOOL),
        "Thread32Next": ([w.HANDLE, w.LPVOID], w.BOOL),
        "OpenThread": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        "ResumeThread": ([w.HANDLE], w.DWORD),
    }
    for name, (arguments, result) in signatures.items():
        getattr(api, name).argtypes = arguments
        getattr(api, name).restype = result
    return api


class _WindowsJob:
    """A private kill-on-close job; assignment precedes the child's first code."""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes as w

        class Basic(ctypes.Structure):
            _fields_ = [
                ("process_time", ctypes.c_longlong),
                ("job_time", ctypes.c_longlong),
                ("flags", w.DWORD),
                ("min_working", ctypes.c_size_t),
                ("max_working", ctypes.c_size_t),
                ("active", w.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", w.DWORD),
                ("scheduling", w.DWORD),
            ]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("basic", Basic),
                ("io", ctypes.c_ulonglong * 6),
                ("process_memory", ctypes.c_size_t),
                ("job_memory", ctypes.c_size_t),
                ("peak_process", ctypes.c_size_t),
                ("peak_job", ctypes.c_size_t),
            ]

        self.api = _windows_api()
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError("job creation unavailable")
        limits = Extended()
        limits.basic.flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            self.api.CloseHandle(self.handle)
            self.handle = None
            raise OSError("job containment unavailable")

    def assign_and_resume(self, pid: int) -> None:
        process = self.api.OpenProcess(0x0101, False, pid)
        if not process:
            raise OSError("suspended process unavailable")
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise OSError("job assignment unavailable")
            _resume_primary_thread(self.api, pid)
        finally:
            self.api.CloseHandle(process)

    def close(self) -> bool:
        if self.handle is None:
            return True
        terminated = self.api.TerminateJobObject(self.handle, 1)
        closed = self.api.CloseHandle(self.handle)
        self.handle = None
        return bool(terminated and closed)


def _resume_primary_thread(api: Any, pid: int) -> None:
    """Find the still-suspended primary thread through documented Toolhelp APIs."""
    import ctypes
    from ctypes import wintypes as w

    class ThreadEntry(ctypes.Structure):
        _fields_ = [
            ("size", w.DWORD),
            ("usage", w.DWORD),
            ("thread_id", w.DWORD),
            ("process_id", w.DWORD),
            ("priority", w.LONG),
            ("delta", w.LONG),
            ("flags", w.DWORD),
        ]

    snapshot = api.CreateToolhelp32Snapshot(0x00000004, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError("thread snapshot unavailable")
    try:
        entry = ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        found = api.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.process_id == pid:
                _resume_thread(api, entry.thread_id)
                return
            found = api.Thread32Next(snapshot, ctypes.byref(entry))
        raise OSError("suspended primary thread unavailable")
    finally:
        api.CloseHandle(snapshot)


def _resume_thread(api: Any, thread_id: int) -> None:
    thread = api.OpenThread(0x0002, False, thread_id)
    if not thread:
        raise OSError("primary thread unavailable")
    try:
        if api.ResumeThread(thread) != 1:
            raise OSError("primary thread was not suspended")
    finally:
        api.CloseHandle(thread)
