"""Helpers for subprocess-backed CLI smoke tests."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO_COMMAND_TIMEOUT_SECONDS = 60.0


def resolve_scripts_inventory_json_timeout_seconds(
    *,
    platform: str = sys.platform,
) -> float:
    """Return subprocess timeout for ``check_scripts_inventory.py --json`` smoke tests.

      The JSON stdout path skips repository-wide reference discovery, but Windows
    runs on slow repo mounts still need more headroom than the default 60s helper
      budget for Python startup and script enumeration.
    """
    if platform == "win32":
        return 180.0
    return 90.0


def repo_root() -> Path:
    """Return the repository root used by subprocess-backed test helpers."""
    return REPO_ROOT


def _windows_subprocess_kwargs() -> dict[str, object]:
    """Return kwargs that avoid console popups and improve Windows kill behavior."""
    if sys.platform != "win32":
        return {}
    kwargs: dict[str, object] = {}
    create_no_window = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if create_no_window:
        kwargs["creationflags"] = create_no_window
    return kwargs


def run_repo_command(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = DEFAULT_REPO_COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Run a repository-relative subprocess command with stable defaults.

    Subprocess smoke tests should fail locally instead of waiting for the
    suite-level pytest-timeout when a delegated CLI blocks before closing pipes.

    On Windows, stdout/stderr are file-backed (not ``capture_output`` PIPEs).
    PIPE + ``timeout`` can hang forever in ``communicate()`` cleanup when the
    child is stuck, which races pytest-timeout and surfaces as a 60s hang under
    PyCharm even for fast commands like ``run_tests.py help``.
    """
    command = list(args)
    workdir = cwd or REPO_ROOT
    merged_env = None if env is None else os.environ | env

    stdout_handle = tempfile.NamedTemporaryFile(
        prefix="bioetl_cli_stdout_",
        suffix=".txt",
        delete=False,
    )
    stderr_handle = tempfile.NamedTemporaryFile(
        prefix="bioetl_cli_stderr_",
        suffix=".txt",
        delete=False,
    )
    stdout_path = Path(stdout_handle.name)
    stderr_path = Path(stderr_handle.name)
    stdout_handle.close()
    stderr_handle.close()

    try:
        with (
            stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_file,
            stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_file,
        ):
            completed = subprocess.run(
                command,
                cwd=workdir,
                env=merged_env,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout,
                **_windows_subprocess_kwargs(),
            )
        return subprocess.CompletedProcess(
            args=command,
            returncode=completed.returncode,
            stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
            stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
        )
    except subprocess.TimeoutExpired as exc:
        # Re-raise with captured partial output when available (no PIPE drain hang).
        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=exc.timeout,
            output=stdout_path.read_text(encoding="utf-8", errors="replace"),
            stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
        ) from None
    finally:
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)


def run_repo_python(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = DEFAULT_REPO_COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Run one Python command from the repository root by default."""
    return run_repo_command(
        sys.executable,
        *args,
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


def run_python_cli(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = DEFAULT_REPO_COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Backward-compatible alias for repository-root Python CLI execution."""
    return run_repo_python(
        *args,
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


def run_main_in_process(
    main_fn: Callable[[list[str] | None], int | None],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Run one main(argv) function in-process and capture stdout/stderr."""
    stdout = StringIO()
    stderr = StringIO()
    returncode = 0
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            result = main_fn(list(args))
        except SystemExit as exc:
            code = exc.code
            returncode = code if isinstance(code, int) else (0 if code is None else 1)
        else:
            returncode = 0 if result is None else int(result)
    return subprocess.CompletedProcess(
        args=list(args),
        returncode=returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def assert_router_python_command(
    router_module: ModuleType,
    command_name: str,
    *,
    expected_target: str,
) -> None:
    """Assert that one delegated router command targets the expected Python script."""
    spec = router_module.COMMAND_SPECS[command_name]
    assert spec.runner == "python"
    assert spec.target == expected_target


def assert_process_succeeded(result: subprocess.CompletedProcess[str]) -> None:
    """Assert a subprocess exited successfully, surfacing stderr or stdout."""
    assert result.returncode == 0, result.stderr or result.stdout


def assert_cli_succeeded(result: subprocess.CompletedProcess[str]) -> None:
    """Backward-compatible alias for successful CLI process assertions."""
    assert_process_succeeded(result)
