"""Run portable host-dispatch behavior tests without starting an MCP provider."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


@pytest.mark.skipif(
    shutil.which("node") is None, reason="Node is required for host dispatch"
)
def test_host_transport_behavior() -> None:
    result = subprocess.run(
        [
            shutil.which("node") or "node",
            "--test",
            str(Path(__file__).with_name("test_host_transport.mjs")),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
