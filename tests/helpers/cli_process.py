"""Helpers for subprocess-backed CLI smoke tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """Return the repository root used by subprocess-backed test helpers."""
    return REPO_ROOT


def run_repo_command(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a repository-relative subprocess command with stable defaults."""
    return subprocess.run(
        list(args),
        cwd=cwd or REPO_ROOT,
        env=None if env is None else os.environ | env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def run_repo_python(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
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
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Backward-compatible alias for repository-root Python CLI execution."""
    return run_repo_python(
        *args,
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


def assert_process_succeeded(result: subprocess.CompletedProcess[str]) -> None:
    """Assert a subprocess exited successfully, surfacing stderr or stdout."""
    assert result.returncode == 0, result.stderr or result.stdout


def assert_cli_succeeded(result: subprocess.CompletedProcess[str]) -> None:
    """Backward-compatible alias for successful CLI process assertions."""
    assert_process_succeeded(result)
