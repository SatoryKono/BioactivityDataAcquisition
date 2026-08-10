"""Locking and platform-installer contracts for optional vendor tools."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[5]


def test_optional_vendor_extras_are_exact_and_absent_from_core_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    extras = project["optional-dependencies"]
    expected = {
        "agentdebugx": ["agentdebugx==0.3.1"],
        "proofagent": ["proofagent-harness==0.11.0"],
        "agent-tools": ["agentdebugx==0.3.1", "proofagent-harness==0.11.0"],
    }
    assert {name: extras[name] for name in expected} == expected
    core = "\n".join(project["dependencies"]).lower()
    assert "agentdebugx" not in core
    assert "proofagent" not in core


def test_lock_contains_approved_wheel_hashes() -> None:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "agentdebugx-0.3.1-py3-none-any.whl" in lock
    assert (
        "sha256:4199bd0be46e7b904da782eea02e330a00e6dd4a66fc66458259ec73bdb9b85b"
        in lock
    )
    assert "proofagent_harness-0.11.0-py3-none-any.whl" in lock
    assert (
        "sha256:9cc8f86f4ab4c7e7516f4549e0aa957fd5cc018e2f26806912d2ce7e94cf48ae"
        in lock
    )


def test_platform_installers_default_to_none_and_isolate_optional_failures() -> None:
    wsl = (ROOT / "scripts/engineering/dev/setup_env_wsl.sh").read_text(
        encoding="utf-8"
    )
    windows = (ROOT / "scripts/engineering/dev/setup_env_windows.ps1").read_text(
        encoding="utf-8"
    )

    assert 'AGENT_TOOLS="none"' in wsl
    assert '[string]$AgentTools = "none"' in windows
    assert 'for EXTRA in "${OPTIONAL_EXTRAS[@]}"' in wsl
    assert "foreach ($Extra in $OptionalExtras)" in windows
    assert "without blocking the remaining tools" in wsl
    assert "without blocking the remaining tools" in windows
    assert "--frozen" in wsl
    assert '"--frozen"' in windows
    assert "--no-build" in wsl
    assert '"--no-build"' in windows


def test_rollback_is_documented_without_env_mutation() -> None:
    readme = (ROOT / "scripts/ai/agent_tools/README.md").read_text(
        encoding="utf-8"
    )
    assert "## Uninstall and rollback" in readme
    assert "pip uninstall agentdebugx proofagent-harness" in readme
    assert "requires no code or configuration rollback" in readme
