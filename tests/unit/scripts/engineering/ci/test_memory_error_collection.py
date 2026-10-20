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

    # 2. Run pytest directly. Collection MemoryError is a pytest exit 2.
    # The diagnostic adapter is covered by test_memory_error_keeps_traceback_without_claiming_oom.
    cmd = [sys.executable, "-m", "pytest", str(test_file)]

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # 3. Check the exit code and that the traceback names the collection frame.
    combined = f"{res.stdout}\n{res.stderr}"
    assert res.returncode == 2
    assert "test_fake_memory_error.py" in combined
    assert "MemoryError: synthetic-collection-memory-error" in combined
