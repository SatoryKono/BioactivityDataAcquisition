import pytest
import sys
from pathlib import Path
import subprocess


@pytest.mark.serial
def test_memory_error_during_collection(tmp_path: Path) -> None:
    # 1. Create a fake test file that raises MemoryError during collection
    test_file = tmp_path / "test_fake_memory_error.py"
    test_file.write_text(
        "import pytest\n"
        "raise MemoryError('synthetic-collection-memory-error')\n"
        "def test_dummy():\n"
        "    pass\n"
    )

    # 2. Run the diagnostic adapter against this file
    evidence_file = tmp_path / "junit.xml"
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()

    # Run the test using pytest directly
    cmd = [sys.executable, "-m", "pytest", str(test_file)]

    res = subprocess.run(cmd, capture_output=True, text=True)

    # 3. Check the exit code and that the error is in the output
    # Pytest returns 2 for collection errors
    assert res.returncode == 2
    assert (
        "MemoryError: synthetic-collection-memory-error" in res.stderr
        or "MemoryError: synthetic-collection-memory-error" in res.stdout
    )
