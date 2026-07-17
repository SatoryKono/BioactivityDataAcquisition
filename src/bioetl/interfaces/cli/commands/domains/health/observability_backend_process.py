"""Detached observability backend process helpers."""

from __future__ import annotations

import os
import signal
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _resolve_system_executable(command: str) -> str | None:
    """Return an absolute executable path when available."""
    return which(command)


def _as_sorted_pid_tuple(values: set[int]) -> tuple[int, ...]:
    return tuple(sorted(values))


def _try_parse_pid(pid_text: str) -> int | None:
    try:
        return int(pid_text)
    except ValueError:
        return None


def _parse_windows_netstat_listener_pids(output: str, port: int) -> tuple[int, ...]:
    suffix = f":{port}"
    pids: set[int] = set()
    for line in output.splitlines():
        normalized = line.split()
        if len(normalized) < 5:
            continue
        local_address, state, pid_text = normalized[1], normalized[3], normalized[4]
        if state.upper() != "LISTENING" or not local_address.endswith(suffix):
            continue
        if (pid := _try_parse_pid(pid_text)) is not None:
            pids.add(pid)
    return _as_sorted_pid_tuple(pids)


def _parse_posix_ss_listener_pids(output: str, port: int) -> tuple[int, ...]:
    suffix = f":{port}"
    pids: set[int] = set()
    for line in output.splitlines():
        if suffix not in line or "LISTEN" not in line:
            continue
        for remainder in line.split("pid=")[1:]:
            pid_text = remainder.split(",", maxsplit=1)[0].split(")", maxsplit=1)[0]
            if (pid := _try_parse_pid(pid_text)) is not None:
                pids.add(pid)
    return _as_sorted_pid_tuple(pids)


def _run_listener_probe(command: list[str]) -> str:
    result = subprocess.run(  # nosec B603
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _find_windows_listener_pids_by_port(port: int) -> tuple[int, ...]:
    netstat = _resolve_system_executable("netstat")
    if netstat is None:
        return ()
    output = _run_listener_probe([netstat, "-ano", "-p", "tcp"])
    return _parse_windows_netstat_listener_pids(output, port)


def _find_posix_listener_pids_by_port(port: int) -> tuple[int, ...]:
    ss = _resolve_system_executable("ss")
    if ss is None:
        return ()
    output = _run_listener_probe([ss, "-ltnp"])
    return _parse_posix_ss_listener_pids(output, port)


def _find_listening_backend_pids_by_port(port: int) -> tuple[int, ...]:
    if os.name == "nt":
        return _find_windows_listener_pids_by_port(port)
    return _find_posix_listener_pids_by_port(port)


def _find_listening_backend_pid_by_port(port: int) -> int | None:
    pids = _find_listening_backend_pids_by_port(port)
    return pids[0] if pids else None


def find_listening_backend_pid_by_port(port: int) -> int | None:
    """Return one listening backend PID for a port when one is currently bound."""
    return _find_listening_backend_pid_by_port(port)


def drop_listening_backend_on_port(
    port: int,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Terminate the current listener on one port so a fresh backend can bind."""
    pids = _find_listening_backend_pids_by_port(port)
    if not pids:
        return True
    if not _drop_listener_pids(port, pids):
        return False
    sleep_fn(0.5)
    return not _find_listening_backend_pids_by_port(port)


def _drop_listener_pids(port: int, pids: tuple[int, ...]) -> bool:
    drop_pid = (
        _drop_windows_listener_pid if os.name == "nt" else _drop_posix_listener_pid
    )
    return all(drop_pid(port, pid) for pid in pids)


def _drop_windows_listener_pid(port: int, pid: int) -> bool:
    taskkill_result = _run_taskkill(pid)
    if taskkill_result.returncode == 0 or not _pid_still_listening(port, pid):
        return True
    return _terminate_pid_with_sigterm(port, pid)


def _run_taskkill(pid: int) -> subprocess.CompletedProcess[str]:
    taskkill = _resolve_system_executable("taskkill")
    if taskkill is None:
        return subprocess.CompletedProcess(args=(), returncode=1)
    return subprocess.run(  # nosec B603
        [taskkill, "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )


def _drop_posix_listener_pid(port: int, pid: int) -> bool:
    return _terminate_pid_with_sigterm(port, pid)


def _terminate_pid_with_sigterm(port: int, pid: int) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return not _pid_still_listening(port, pid)
    return True


def _pid_still_listening(port: int, pid: int) -> bool:
    return pid in _find_listening_backend_pids_by_port(port)


def _build_detached_backend_popen_kwargs(
    *,
    os_name: str = os.name,
    subprocess_module: object = subprocess,
) -> dict[str, object]:
    """Build platform-specific detached subprocess kwargs for the backend."""
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os_name == "nt":
        detached_process = int(getattr(subprocess_module, "DETACHED_PROCESS", 0))
        new_process_group = int(
            getattr(subprocess_module, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        create_no_window = int(getattr(subprocess_module, "CREATE_NO_WINDOW", 0))
        kwargs["creationflags"] = (
            detached_process | new_process_group | create_no_window
        )

        startupinfo_factory = getattr(subprocess_module, "STARTUPINFO", None)
        if callable(startupinfo_factory):
            startupinfo = startupinfo_factory()
            startf_use_show_window = int(
                getattr(subprocess_module, "STARTF_USESHOWWINDOW", 0)
            )
            has_sw_hide = hasattr(subprocess_module, "SW_HIDE")
            sw_hide = int(getattr(subprocess_module, "SW_HIDE", 0))
            if startf_use_show_window:
                existing_dw_flags = (
                    int(startupinfo.dwFlags) if hasattr(startupinfo, "dwFlags") else 0
                )
                startupinfo.dwFlags = existing_dw_flags | startf_use_show_window
            if has_sw_hide:
                startupinfo.wShowWindow = sw_hide
            kwargs["startupinfo"] = startupinfo
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _build_detached_backend_env(
    *,
    current_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Ensure detached backend subprocess can import the src-layout package."""
    env = dict(current_env if current_env is not None else os.environ)
    src_root = Path(__file__).resolve().parents[6]
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    pythonpath_parts = [str(src_root)]
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def build_detached_backend_log_path(port: int) -> Path:
    """Return the deterministic detached backend startup log path for one port."""
    return Path(tempfile.gettempdir()) / f"bioetl-quarantine-backend-{port}.log"


def start_detached_quarantine_backend(
    *,
    bind_host: str = "0.0.0.0",
    port: int = DEFAULT_HEALTH_SERVER_PORT,
    python_executable: str | None = None,
    data_root: Path | None = None,
    popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> subprocess.Popen[bytes]:
    """Launch ``bioetl quarantine serve`` as a detached background process."""
    command = [
        python_executable or sys.executable,
        "-m",
        "bioetl",
        "quarantine",
        "serve",
        "--host",
        bind_host,
        "--port",
        str(port),
    ]
    if data_root is not None:
        if not data_root.is_absolute():
            raise ValueError("data_root must be an absolute path")
        command.extend(("--data-root", str(data_root.resolve(strict=True))))
    kwargs = _build_detached_backend_popen_kwargs()
    kwargs.pop("stdout", None)
    kwargs.pop("stderr", None)
    kwargs["cwd"] = str(Path(__file__).resolve().parents[7])
    kwargs["env"] = _build_detached_backend_env()
    log_path = build_detached_backend_log_path(port)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    with log_path.open("ab") as log_handle:
        return popen_factory(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            **kwargs,
        )


def python_executable_to_tuple(args: object) -> tuple[str, ...]:
    """Normalize subprocess ``args`` into a tuple for stable reporting/tests."""
    if isinstance(args, (list, tuple)):
        return tuple(str(item) for item in args)
    return (str(args),)


__all__ = [
    "build_detached_backend_log_path",
    "drop_listening_backend_on_port",
    "find_listening_backend_pid_by_port",
    "python_executable_to_tuple",
    "start_detached_quarantine_backend",
]
