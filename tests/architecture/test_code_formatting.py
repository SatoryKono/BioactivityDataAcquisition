"""Architecture test: проверка форматирования кода с помощью ruff.

REQ-ARCH-050: Consistent code formatting across the codebase.

Note: Uses ruff format which is compatible with black formatting style
(configured via profile = "black" in pyproject.toml).
"""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestCodeFormatting:
    """Tests ensuring code follows consistent formatting standards."""

    @pytest.mark.slow
    def test_ruff_formatting_src(self) -> None:
        """Source code MUST be formatted with ruff format.

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
            "Run `ruff format src` to fix formatting issues."
        )

    @pytest.mark.slow
    def test_ruff_formatting_tests(self) -> None:
        """Test code MUST be formatted with ruff format.

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
            "Run `ruff format tests` to fix formatting issues."
        )
