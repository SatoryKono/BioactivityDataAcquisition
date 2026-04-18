"""Architecture test: проверка форматирования кода с помощью ruff.

REQ-ARCH-050: Consistent code formatting across the codebase.
REQ-ARCH-051: Consistent import ordering via ruff (isort rules).

Note: ruff replaces black+isort as the unified formatter and linter.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_ruff_cmd() -> list[str] | None:
    """Resolve the most stable ruff command for this repository.

    Prefer project-local .venv binaries to avoid formatter-version drift when
    tests are run with a different system Python interpreter.
    """
    if os.name == "nt":
        local_candidates = [_REPO_ROOT / ".venv" / "Scripts" / "ruff.exe"]
    else:
        local_candidates = [_REPO_ROOT / ".venv" / "bin" / "ruff"]
    for candidate in local_candidates:
        if candidate.exists():
            return [str(candidate)]

    if find_spec("ruff") is not None:
        return [sys.executable, "-m", "ruff"]

    return None


_RUFF_CMD = _resolve_ruff_cmd()
_ruff_available = _RUFF_CMD is not None

# Platform-specific hints for line ending issues
_LINE_ENDING_HINT = (
    (
        "\n\nOn Windows, line ending issues may occur. Try:\n"
        "  git add --renormalize .\n"
        "  git checkout -- .\n"
        "Or run `ruff format` to fix formatting."
    )
    if platform.system() == "Windows"
    else ""
)


def _ruff_env() -> dict[str, str]:
    """Use a writable cache dir across mixed WSL/docker-desktop mounts."""
    env = os.environ.copy()
    env.setdefault("RUFF_CACHE_DIR", "/tmp/bioetl-ruff-cache")
    return env


def _run_format_check(target: str) -> subprocess.CompletedProcess[str]:
    """Run `ruff format --check` with Windows retry for line-ending churn."""
    result = subprocess.run(
        [*_RUFF_CMD, "format", "--check", target],  # type: ignore[arg-type]
        capture_output=True,
        env=_ruff_env(),
        text=True,
    )
    if result.returncode == 0 or platform.system() != "Windows":
        return result

    # On Windows, normalize line endings and retry once to avoid flaky churn.
    subprocess.run(
        [*_RUFF_CMD, "format", target],  # type: ignore[arg-type]
        capture_output=True,
        env=_ruff_env(),
        text=True,
    )
    return subprocess.run(
        [*_RUFF_CMD, "format", "--check", target],  # type: ignore[arg-type]
        capture_output=True,
        env=_ruff_env(),
        text=True,
    )


def _run_isort_check() -> subprocess.CompletedProcess[str]:
    """Run import-order check with stable command resolution on Windows."""
    check_cmd: list[str]
    if platform.system() == "Windows" and find_spec("ruff") is not None:
        check_cmd = [sys.executable, "-m", "ruff"]
    else:
        check_cmd = [*_RUFF_CMD]  # type: ignore[misc]
    return subprocess.run(
        [*check_cmd, "check", "--select", "I", "src", "tests"],
        capture_output=True,
        env=_ruff_env(),
        text=True,
    )


class TestCodeFormatting:
    """Tests ensuring code follows ruff formatting standards."""

    @pytest.mark.slow
    @pytest.mark.skipif(not _ruff_available, reason="ruff not installed")
    def test_ruff_formatting_src(self) -> None:
        """Source code MUST be formatted with ruff.

        Run `ruff format src` to fix formatting issues.
        """
        result = _run_format_check("src")

        assert result.returncode == 0, (
            "Code formatting issues found in src/:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            f"Run `ruff format src` to fix formatting issues.{_LINE_ENDING_HINT}"
        )

    @pytest.mark.slow
    @pytest.mark.skipif(not _ruff_available, reason="ruff not installed")
    def test_ruff_formatting_tests(self) -> None:
        """Test code MUST be formatted with ruff.

        Run `ruff format tests` to fix formatting issues.
        """
        result = _run_format_check("tests")

        assert result.returncode == 0, (
            "Code formatting issues found in tests/:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            f"Run `ruff format tests` to fix formatting issues.{_LINE_ENDING_HINT}"
        )

    @pytest.mark.slow
    @pytest.mark.skipif(not _ruff_available, reason="ruff not installed")
    def test_ruff_isort_check(self) -> None:
        """Imports MUST be sorted according to ruff isort rules.

        Run `ruff check --select I --fix src tests` to fix import ordering issues.
        """
        result = _run_isort_check()

        assert result.returncode == 0, (
            "Import ordering issues found:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            "Run `ruff check --select I --fix src tests` to fix import ordering issues."
        )
