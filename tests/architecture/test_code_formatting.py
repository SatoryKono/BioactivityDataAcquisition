"""Architecture test: проверка форматирования кода с помощью black и isort.

REQ-ARCH-050: Consistent code formatting across the codebase.
REQ-ARCH-051: Consistent import ordering via isort.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from importlib.util import find_spec

import pytest

# Check if black is available
_black_available = find_spec("black") is not None
# Check if isort is available
_isort_available = find_spec("isort") is not None

# Platform-specific hints for line ending issues
_LINE_ENDING_HINT = (
    (
        "\n\nOn Windows, line ending issues may occur. Try:\n"
        "  git add --renormalize .\n"
        "  git checkout -- .\n"
        "Or run `black` to fix formatting."
    )
    if platform.system() == "Windows"
    else ""
)


class TestCodeFormatting:
    """Tests ensuring code follows black formatting standards."""

    @pytest.mark.slow
    @pytest.mark.skipif(not _black_available, reason="black not installed")
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
            f"Run `black src` to fix formatting issues.{_LINE_ENDING_HINT}"
        )

    @pytest.mark.slow
    @pytest.mark.skipif(not _black_available, reason="black not installed")
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
            f"Run `black tests` to fix formatting issues.{_LINE_ENDING_HINT}"
        )

    @pytest.mark.slow
    @pytest.mark.skipif(not _isort_available, reason="isort not installed")
    def test_isort_check(self) -> None:
        """Imports MUST be sorted with isort.

        Run `isort src tests` to fix import ordering issues.
        """
        result = subprocess.run(
            [sys.executable, "-m", "isort", "--check-only", "src", "tests"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            "Import ordering issues found:\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            "Run `isort src tests` to fix import ordering issues."
        )
