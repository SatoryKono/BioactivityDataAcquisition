"""Run portable managed GitHub handoff regressions without provider/API calls."""
from pathlib import Path
import shutil
import subprocess

import pytest


def test_managed_github_transport_contract() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the GitHub transport protocol tests")
    source = Path(__file__).with_suffix(".mjs")
    result = subprocess.run(
        [node, "--test", str(source)],
        cwd=Path(__file__).resolve().parents[6],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
