"""Smoke test for the eager merger input measurement harness."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.serial]


def test_measurement_harness_smoke():
    """Verify that the measurement harness runs successfully on a minimal scale."""
    harness_path = Path("scripts/engineering/performance/measure_merger_input.py")
    assert harness_path.exists(), "Measurement harness script not found."

    # Run the worker directly with a small scale to ensure no crashes
    cmd = [
        sys.executable,
        str(harness_path),
        "--worker",
        "100",
        "--out",
        "smoke_test_out.json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    assert result.returncode == 0, (
        f"Harness worker failed with exit code {result.returncode}.\nStderr: {result.stderr}"
    )

    out_file = Path("smoke_test_out.json")
    assert out_file.exists(), "Harness worker did not produce output JSON."

    # Clean up the test artifact
    out_file.unlink()
