"""Tests for interfaces/cli/__main__.py module.

Verifies the CLI can be invoked as a module.
"""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import click
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
        from bioetl.interfaces.cli.__main__ import main
        from bioetl.interfaces.cli.main import main as main_from_module

        # They should be the same function
        assert main is main_from_module

    def test_top_level_module_entrypoint_delegates_to_cli_main(self) -> None:
        """The retained python -m bioetl seam must stay a thin CLI delegate."""
        calls: list[str] = []

        with patch(
            "bioetl.interfaces.cli._main_module.main",
            side_effect=lambda: calls.append("main"),
        ):
            runpy.run_module("bioetl", run_name="__main__")

        assert calls == ["main"]

    def test_cli_package_module_entrypoint_delegates_to_cli_main(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The retained python -m bioetl.interfaces.cli seam must stay a thin CLI delegate."""
        calls: list[str] = []
        monkeypatch.delitem(
            sys.modules,
            "bioetl.interfaces.cli.__main__",
            raising=False,
        )

        with patch(
            "bioetl.interfaces.cli.main.main",
            side_effect=lambda: calls.append("main"),
        ):
            runpy.run_module("bioetl.interfaces.cli", run_name="__main__")

        assert calls == ["main"]

    def test_lazy_command_loader_resolves_only_requested_public_command(self) -> None:
        """Lazy command loading should keep the CLI entrypoint as a thin seam."""
        from bioetl.interfaces.cli.main import _load_cli_command

        command = click.Command("run-all")

        with patch(
            "bioetl.interfaces.cli.main.import_module",
            return_value=SimpleNamespace(run_all=command),
        ) as import_module:
            loaded = _load_cli_command("run-all")

        assert loaded is command
        import_module.assert_called_once_with("bioetl.interfaces.cli.commands.run_all")

    def test_lazy_command_loader_returns_none_for_unknown_command(self) -> None:
        """Unknown command names must fail fast without importing command modules."""
        from bioetl.interfaces.cli.main import _load_cli_command

        with patch("bioetl.interfaces.cli.main.import_module") as import_module:
            assert _load_cli_command("not-a-command") is None

        import_module.assert_not_called()

    @pytest.mark.slow
    @pytest.mark.timeout(120)  # Extended timeout for subprocess on Windows
    def test_module_runnable_with_help(self) -> None:
        """Test module can be run with --help flag (subprocess-based, slow)."""
        # Set PYTHONPATH to include src directory for subprocess
        src_path = Path(__file__).parent.parent.parent.parent.parent / "src"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_path)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "bioetl.interfaces.cli", "--help"],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            pytest.fail(f"CLI help subprocess timed out unexpectedly: {exc}")

        # Help should exit with 0 and show usage info
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Usage" in result.stdout or "usage" in result.stdout.lower()
