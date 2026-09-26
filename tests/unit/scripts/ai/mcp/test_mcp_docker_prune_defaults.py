"""MCP docker prune helpers must default to dry-run on every platform."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[5]
PS1 = REPO_ROOT / "scripts" / "ai" / "mcp" / "support" / "mcp_docker_prune.ps1"
SH = REPO_ROOT / "scripts" / "ai" / "mcp" / "support" / "mcp_docker_prune.sh"


def test_powershell_prune_defaults_to_dry_run() -> None:
    source = PS1.read_text(encoding="utf-8")
    assert "MCP_DOCKER_PRUNE_APPLY" in source
    assert "$apply = $env:MCP_DOCKER_PRUNE_APPLY -eq '1'" in source
    assert "$dryRun = $forceDryRun -or -not $apply" in source
    apply_idx = source.index("MCP_DOCKER_PRUNE_APPLY")
    rm_idx = source.index("docker rm -f")
    assert apply_idx < rm_idx


def test_bash_prune_defaults_to_dry_run() -> None:
    source = SH.read_text(encoding="utf-8")
    assert 'apply="${2:-${MCP_DOCKER_PRUNE_APPLY:-0}}"' in source
    assert "Default is dry-run" in source
    apply_idx = source.index("MCP_DOCKER_PRUNE_APPLY")
    rm_idx = source.index("docker rm -f")
    assert apply_idx < rm_idx
