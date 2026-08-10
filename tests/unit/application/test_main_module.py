import sys
import subprocess
from pathlib import Path
from unittest import mock

import runpy

from bioetl.__main__ import _clear_known_stale_windows_bytecode

pytestmark = pytest.mark.unit


def test_clear_known_stale_windows_bytecode_non_win32():
    with mock.patch("sys.platform", "linux"):
        with mock.patch("importlib.invalidate_caches") as mock_invalidate:
            _clear_known_stale_windows_bytecode()
            mock_invalidate.assert_not_called()


def test_clear_known_stale_windows_bytecode_win32():
    with mock.patch("sys.platform", "win32"):
        with mock.patch("pathlib.Path.unlink") as mock_unlink:
            with mock.patch("importlib.invalidate_caches") as mock_invalidate:
                _clear_known_stale_windows_bytecode()
                mock_unlink.assert_called_once_with(missing_ok=True)
                mock_invalidate.assert_called_once()


def test_clear_known_stale_windows_bytecode_win32_oserror():
    with mock.patch("sys.platform", "win32"):
        with mock.patch("pathlib.Path.unlink", side_effect=OSError("test")):
            with mock.patch("importlib.invalidate_caches") as mock_invalidate:
                # Should suppress OSError and continue
                _clear_known_stale_windows_bytecode()
                mock_invalidate.assert_called_once()


def test_main_block_executed_via_subprocess():
    """Test the complete __main__.py execution via subprocess."""
    result = subprocess.run(
        [sys.executable, "-m", "bioetl", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout or "usage:" in result.stdout


def test_main_block_executed_directly():
    """Test the __main__ block behavior directly via run_path."""
    with mock.patch("bioetl.interfaces.cli.main") as mock_main:
        with mock.patch("sys.platform", "linux"):
            # run_path properly sets up the environment as if executing the file
            main_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "src"
                / "bioetl"
                / "__main__.py"
            )
            runpy.run_path(str(main_path), run_name="__main__")
            mock_main.assert_called_once()


def test_main_block_not_executed():
    """Test that main() is NOT called when imported as a module."""
    with mock.patch("bioetl.interfaces.cli.main") as mock_main:
        with mock.patch("sys.platform", "linux"):
            main_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "src"
                / "bioetl"
                / "__main__.py"
            )
            runpy.run_path(str(main_path), run_name="bioetl.__main__")
            mock_main.assert_not_called()
