"""Detached observability backend process helpers."""

from __future__ import annotations

import os
import signal
import subprocess  # nosec
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _find_listening_backend_pid_by_port(port: int) -> int | None:
    if os.name == "nt":
        result = subprocess.run(  # nosec
            ["netstat", "-ano", "-p", "tcp"],
            check=False,
            capture_output=True,
            text=True,
        )
        suffix = f":{port}"
        for line in result.stdout.splitlines():
            normalized = line.split()
            if len(normalized) < 5:
                continue
            local_address, state, pid_text = normalized[1], normalized[3], normalized[4]
            if state.upper() != "LISTENING" or not local_address.endswith(suffix):
                continue
            try:
                return int(pid_text)
            except ValueError:
                continue
        return None

    result = subprocess.run(  # nosec
        ["ss", "-ltnp"],
        check=False,
        capture_output=True,
        text=True,
    )
    suffix = f":{port}"
    for line in result.stdout.splitlines():
        if suffix not in line or "LISTEN" not in line:
            continue
        pid_marker = "pid="
        if pid_marker not in line:
            continue
        remainder = line.split(pid_marker, maxsplit=1)[1]
        pid_text = remainder.split(",", maxsplit=1)[0].split(")", maxsplit=1)[0]
        try:
            return int(pid_text)
        except ValueError:
            continue
    return None


def drop_listening_backend_on_port(
    port: int,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Terminate the current listener on one port so a fresh backend can bind."""
    pid = _find_listening_backend_pid_by_port(port)
    if pid is None:
        return True
    try:
        if os.name == "nt":
            result = subprocess.run(  # nosec
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    sleep_fn(0.5)
    return _find_listening_backend_pid_by_port(port) is None


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
