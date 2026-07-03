"""Architecture gate for pipeline-config-contract ownership map artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_ARTIFACT = (
    PROJECT_ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)


@pytest.mark.architecture
def test_pipeline_config_contract_ownership_map_is_current() -> None:
    """Ownership map JSON must match the generator output."""
    assert JSON_ARTIFACT.exists(), (
        "Missing pipeline-config-contract ownership map artifact; regenerate with "
        "python -m scripts.engineering.qa report-pipeline-config-contract-ownership-map"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "report-pipeline-config-contract-ownership-map",
            "--check",
            "--json-out",
            str(JSON_ARTIFACT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
