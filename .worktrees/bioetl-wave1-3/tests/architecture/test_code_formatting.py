"""Architecture test: проверка форматирования кода с помощью ruff.

REQ-ARCH-050: Consistent code formatting across the codebase.
REQ-ARCH-051: Consistent import ordering via ruff (isort rules).

Note: ruff replaces black+isort as the unified formatter and linter.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from importlib.util import find_spec

import pytest

# Check if ruff is available
_ruff_available = find_spec("ruff") is not None

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


class TestCodeFormatting:
    """Tests ensuring code follows ruff formatting standards."""

    @pytest.mark.slow
    @pytest.mark.skipif(not _ruff_available, reason="ruff not installed")
    def test_ruff_formatting_src(self) -> None:
        """Source code MUST be formatted with ruff.

        Run `ruff format src` to fix formatting issues.
        """
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", "src"],
            capture_output=True,
            text=True,
        )

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
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", "tests"],
            capture_output=True,
            text=True,
        )

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
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "I", "src", "tests"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            "Import ordering issues found:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            "Run `ruff check --select I --fix src tests` to fix import ordering issues."
        )
