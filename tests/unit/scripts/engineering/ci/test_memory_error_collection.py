from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.serial
def test_memory_error_during_collection(tmp_path: Path) -> None:
    # 1. Create a fake test file that raises MemoryError during collection
    test_file = tmp_path / "test_fake_memory_error.py"
    test_file.write_text(
        "import pytest\n"
        "raise MemoryError('synthetic-collection-memory-error')\n"
        "def test_dummy():\n"
        "    pass\n",
        encoding="utf-8",
    )

    # Run pytest directly. This test does not start pytest_abort_diagnostic_adapter.
    cmd = [sys.executable, "-m", "pytest", str(test_file)]

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Pytest returns 2 for collection errors.
    combined = f"{res.stdout}\n{res.stderr}"
    assert res.returncode == 2
    assert "test_fake_memory_error.py" in combined
    assert "MemoryError: synthetic-collection-memory-error" in combined
