"""Helpers for subprocess-backed CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_python_cli(
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one Python CLI command from the repository root by default."""
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def assert_cli_succeeded(result: subprocess.CompletedProcess[str]) -> None:
    """Assert a CLI process exited successfully, surfacing stderr on failure."""
    assert result.returncode == 0, result.stderr
