"""Architecture test: проверка форматирования кода с помощью black.

REQ-ARCH-050: Consistent code formatting across the codebase.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestCodeFormatting:
    """Tests ensuring code follows black formatting standards."""

    @pytest.mark.slow
    def test_black_formatting_src(self) -> None:
        """Source code MUST be formatted with black.

        Run `black src` to fix formatting issues.
        """
        result = subprocess.run(
            [sys.executable, "-m", "black", "--check", "src"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            "Code formatting issues found in src/:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            "Run `black src` to fix formatting issues."
        )

    @pytest.mark.slow
    def test_black_formatting_tests(self) -> None:
        """Test code MUST be formatted with black.

        Run `black tests` to fix formatting issues.
        """
        result = subprocess.run(
            [sys.executable, "-m", "black", "--check", "tests"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            "Code formatting issues found in tests/:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            "Run `black tests` to fix formatting issues."
        )
