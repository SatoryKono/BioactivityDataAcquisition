"""Architecture checks for consolidated dev test runner wrappers."""

from __future__ import annotations

from tests.helpers import repo_root, run_repo_python


def test_run_tests_backend_help_works() -> None:
    """Canonical backend should provide help output with zero exit code."""
    root = repo_root()
    result = run_repo_python("scripts/engineering/dev/run_tests.py", "help", cwd=root)
    assert result.returncode == 0, result.stderr
    assert "BioETL Test Runner" in result.stdout


def test_sh_wrapper_delegates_to_backend() -> None:
    """Bash wrapper must stay a thin facade over the Python backend."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/run_tests.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/run_tests.py" in content


def test_ps1_wrapper_delegates_to_backend() -> None:
    """PowerShell wrapper must stay a thin facade over the Python backend."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/run_tests.ps1").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/run_tests.py" in content


def test_changed_wrapper_delegates_to_backend_changed_command() -> None:
    """Legacy changed-tests wrapper must stay a thin facade over run_tests.py."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/test_changed.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/run_tests.py changed" in content
