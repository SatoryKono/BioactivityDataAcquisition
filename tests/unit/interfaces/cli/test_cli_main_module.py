"""Tests for interfaces/cli/__main__.py module.

Verifies the CLI can be invoked as a module.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.unit
class TestCliMainModule:
    """Tests for CLI __main__ module."""

    def test_main_module_imports(self) -> None:
        """Test that __main__.py can be imported."""
        from bioetl.interfaces.cli import __main__

        assert hasattr(__main__, "main")

    def test_main_function_callable(self) -> None:
        """Test that main function is callable."""
        from bioetl.interfaces.cli.__main__ import main

        assert callable(main)

    def test_module_has_correct_imports(self) -> None:
        """Test module imports from cli.main."""
        from bioetl.interfaces.cli.main import main as main_from_module

        from bioetl.interfaces.cli.__main__ import main

        # They should be the same function
        assert main is main_from_module

    def test_module_runnable_with_help(self) -> None:
        """Test module can be run with --help flag."""
        result = subprocess.run(
            [sys.executable, "-m", "bioetl.interfaces.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Help should exit with 0 and show usage info
        assert result.returncode == 0
        assert "Usage" in result.stdout or "usage" in result.stdout.lower()
