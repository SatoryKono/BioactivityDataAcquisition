"""Single-use Linux supervisor for ordinary and detached check descendants.

Invoked only by process_deadline through private inherited descriptors. The
supervisor is a child subreaper, so setsid/double-fork children are adopted by
this isolated process rather than by a shared multi-threaded caller.
"""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any


class _Stopped(BaseException):
    """A parent stop still requires descendant cleanup."""


def _stop(_signum: int, _frame: Any) -> None:
    raise _Stopped


def _configure(parent_pid: int) -> None:
    """Require actual kernel facilities before launching a check command."""
    _linux_facilities()
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, *([ctypes.c_ulong] * 4)]
    prctl.restype = ctypes.c_int
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    if prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError("subreaper unavailable")
    if prctl(1, signal.SIGTERM, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        raise OSError("parent-death notification unavailable")
    if os.getppid() != parent_pid:
        raise _Stopped
    _children()


def _children() -> list[int]:
    pid = os.getpid()
    path = Path(f"/proc/self/task/{pid}/children")
    return [int(value) for value in path.read_text().split()]


def _linux_facilities() -> dict[str, Any]:
    """Probe platform-specific APIs without assuming Windows stubs have them."""
    api: dict[str, Any] = {
        "open": getattr(os, "pidfd_open", None),
        "signal": getattr(signal, "pidfd_send_signal", None),
        "kill": getattr(signal, "SIGKILL", None),
        "nohang": getattr(os, "WNOHANG", None),
    }
    if any(value is None for value in api.values()):
        raise OSError("pidfd containment unavailable")
    return api


def _kill_owned_child(pid: int) -> None:
    """Verify parent identity after opening a pidfd; never signal a reused PID."""
    fd: int | None = None
    try:
        api = _linux_facilities()
        fd = api["open"](pid, 0)
        stat = Path(f"/proc/{pid}/stat").read_text()
        parent = int(stat.rsplit(")", 1)[1].split()[1])
        if parent == os.getpid():
            api["signal"](fd, api["kill"])
    except (FileNotFoundError, ProcessLookupError):
        pass
    finally:
        if fd is not None:
            os.close(fd)


def _reap(proc: subprocess.Popen[bytes] | None) -> bool:
    """ECHILD proves there are no remaining direct/adopted descendants."""
    while True:
        try:
            pid, status = os.waitpid(-1, _linux_facilities()["nohang"])
        except ChildProcessError:
            return True
        if not pid:
            return False
        if proc is not None and pid == proc.pid:
            proc.returncode = os.waitstatus_to_exitcode(status)


def _cleanup(proc: subprocess.Popen[bytes] | None) -> bool:
    """Kill parents and newly adopted grandchildren until the tree is empty."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        for pid in _children():
            try:
                _kill_owned_child(pid)
            except OSError:
                # Continue cleaning siblings; a survivor still prevents ECHILD.
                pass
        if _reap(proc):
            return True
        time.sleep(0.02)
    return False


def _supervise(config: dict[str, Any]) -> dict[str, Any]:
    proc: subprocess.Popen[bytes] | None = None
    reason = "containment_unavailable"
    cleaned = False
    try:
        _configure(config["parent_pid"])
        reason = "timeout"
        if time.monotonic() < config["deadline"]:
            proc = subprocess.Popen(
                config["argv"],
                cwd=config["cwd"],
                stdin=0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            while time.monotonic() < config["deadline"]:
                if proc.poll() is not None:
                    reason = "completed"
                    break
                time.sleep(0.02)
    except _Stopped:
        reason = "parent_stopped"
    except (OSError, ValueError, TypeError, KeyError):
        reason = "execution_unavailable"
    finally:
        try:
            cleaned = _cleanup(proc)
        except (OSError, ValueError):
            cleaned = False
    return {
        "reason": reason if cleaned else "cleanup_incomplete",
        "returncode": proc.returncode if proc is not None else None,
        "cleaned": cleaned,
    }


def main(config_fd: int, result_fd: int) -> int:
    """No raw exception, command, output or input content reaches the parent."""
    os.set_inheritable(config_fd, False)
    os.set_inheritable(result_fd, False)
    result: dict[str, Any] = {
        "reason": "invalid_request",
        "returncode": None,
        "cleaned": True,
    }
    try:
        with os.fdopen(config_fd, "rb", closefd=False) as stream:
            raw = stream.read(1024 * 1024 + 1)
        config = json.loads(raw) if len(raw) <= 1024 * 1024 else None
        if isinstance(config, dict):
            result = _supervise(config)
    except (OSError, ValueError, TypeError, RecursionError):
        result = {"reason": "supervisor_failure", "returncode": None, "cleaned": False}
    os.write(result_fd, json.dumps(result, separators=(",", ":")).encode())
    return 0
