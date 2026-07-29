# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Opt-in Docker lifecycle smoke; never selected by default CI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.docker_integration]
ROOT = Path(__file__).resolve().parents[2]
MANAGER = ROOT / "scripts/ops/runtime/docker/runtime_manager.py"


@pytest.mark.skipif(
    os.environ.get("BIOETL_RUN_DOCKER_INTEGRATION") != "1",
    reason="requires explicit BIOETL_RUN_DOCKER_INTEGRATION=1 scheduling",
)
def test_main_stack_start_stop_is_idempotent_and_volume_preserving() -> None:
    def run(action: str) -> None:
        completed = subprocess.run(
            [sys.executable, str(MANAGER), action, "--stack", "main"],
            cwd=ROOT,
            check=False,
            timeout=195,
        )
        assert completed.returncode == 0

    def volumes() -> set[str]:
        completed = subprocess.run(
            [
                "docker",
                "volume",
                "ls",
                "--filter",
                "label=com.docker.compose.project=bioetl-main",
                "--format",
                "{{.Name}}",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return set(completed.stdout.splitlines())

    before = volumes()
    run("start")
    run("start")
    run("status")
    run("stop")
    run("stop")
    assert volumes() == before
