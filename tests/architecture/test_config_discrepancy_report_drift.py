"""Drift guard for generated config discrepancy artifacts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_config_discrepancy_report_matches_deterministic_generator() -> None:
    """The config discrepancy report must be executable governance, not stale docs."""
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
    )

    assert result.returncode == 0, (
        "Config comparison matrix/discrepancy report drifted from the generator.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
