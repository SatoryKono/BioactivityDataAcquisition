"""Architecture checks for consolidated dev test runner wrappers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_run_tests_backend_help_works() -> None:
    """Canonical backend should provide help output with zero exit code."""
    root = _project_root()
    result = subprocess.run(
        [sys.executable, "scripts/engineering/dev/run_tests.py", "help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "BioETL Test Runner" in result.stdout


def test_sh_wrapper_delegates_to_backend() -> None:
    """Bash wrapper must stay a thin facade over the Python backend."""
    root = _project_root()
    content = (root / "scripts/engineering/dev/run_tests.sh").read_text(encoding="utf-8")
    assert "scripts/engineering/dev/run_tests.py" in content


def test_ps1_wrapper_delegates_to_backend() -> None:
    """PowerShell wrapper must stay a thin facade over the Python backend."""
    root = _project_root()
    content = (root / "scripts/engineering/dev/run_tests.ps1").read_text(encoding="utf-8")
    assert "scripts/engineering/dev/run_tests.py" in content


def test_changed_wrapper_delegates_to_backend_changed_command() -> None:
    """Legacy changed-tests wrapper must stay a thin facade over run_tests.py."""
    root = _project_root()
    content = (root / "scripts/engineering/dev/test_changed.sh").read_text(encoding="utf-8")
    assert "scripts/engineering/dev/run_tests.py changed" in content
