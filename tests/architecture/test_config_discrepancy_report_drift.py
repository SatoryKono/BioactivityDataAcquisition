"""Drift guard for generated config discrepancy artifacts."""

from __future__ import annotations

import pytest

from pathlib import Path
import sys

pytestmark = [pytest.mark.architecture, pytest.mark.timeout(240)]

ROOT = Path(__file__).resolve().parents[2]


def test_config_discrepancy_report_matches_deterministic_generator(
    cached_subprocess_run,
) -> None:
    """The config discrepancy report must be executable governance, not stale docs."""
    result = cached_subprocess_run(
        [
            sys.executable,
            "-m",
            "scripts.schema",
            "generate-config-matrix",
            "--check",
        ],
        cwd=ROOT,
        timeout=60,
    )

    assert result.returncode == 0, (
        "Config comparison matrix/discrepancy report drifted from the generator.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
