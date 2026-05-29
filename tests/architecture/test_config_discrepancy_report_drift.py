"""Drift guard for generated config discrepancy artifacts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_config_discrepancy_report_matches_deterministic_generator() -> None:
    """The config discrepancy report must be executable governance, not stale docs."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.schema",
                "generate-config-matrix",
                "--check",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as e:
        raise AssertionError(
            f"Config matrix generation timed out after {e.timeout}s. "
            "This may indicate a hang in the script or excessive I/O."
        ) from e

    assert result.returncode == 0, (
        "Config comparison matrix/discrepancy report drifted from the generator.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
