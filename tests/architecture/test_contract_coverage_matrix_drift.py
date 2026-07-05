"""Architecture gate for contract coverage matrix artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_ARTIFACT = PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.json"


@pytest.mark.architecture
def test_contract_coverage_matrix_is_current() -> None:
    """Contract coverage matrix JSON must match the generator output."""
    assert JSON_ARTIFACT.exists(), (
        "Missing contract coverage matrix artifact; regenerate with "
        "python -m scripts.engineering.qa report-contract-coverage-matrix"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "report-contract-coverage-matrix",
            "--check",
            "--json-out",
            str(JSON_ARTIFACT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,  # 2 minutes timeout
    )
    assert result.returncode == 0, result.stderr or result.stdout
