"""Locking and platform-installer contracts for optional vendor tools."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts.ai.agent_tools.__main__ import TOOLS


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[6]


def test_optional_vendor_extras_are_exact_and_absent_from_core_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    extras = project["optional-dependencies"]
    expected = {
        "agentdebugx": ["agentdebugx==0.5.2"],
        "proofagent": ["proofagent-harness==0.13.0"],
        "agent-tools": ["agentdebugx==0.5.2", "proofagent-harness==0.13.0"],
    }
    assert {name: extras[name] for name in expected} == expected
    for name in ("agentdebugx", "proofagent"):
        spec = TOOLS[name]
        assert extras[name] == [f"{spec.distribution}=={spec.expected_version}"]
    core = "\n".join(project["dependencies"]).lower()
    assert "agentdebugx" not in core
    assert "proofagent" not in core


def test_lock_contains_approved_wheel_hashes() -> None:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "agentdebugx-0.5.2-py3-none-any.whl" in lock
    assert (
        "sha256:4fdb90ae19167deb49cbaacce3fbc925220041408aee31c48e59c03bbf7ec82b"
        in lock
    )
    assert "proofagent_harness-0.13.0-py3-none-any.whl" in lock
    assert (
        "sha256:a4013765f2e31b68514f66ac5c7e21709c2036d891ce88b08d7a3e01f8c13527"
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
    assert ".[dev,tests,tracing,$EXTRA]" in wsl
    assert ".[dev,tests,tracing,$Extra]" in windows


def test_rollback_is_documented_without_env_mutation() -> None:
    readme = (ROOT / "scripts/ai/agent_tools/README.md").read_text(encoding="utf-8")
    assert "## Uninstall and rollback" in readme
    assert "pip uninstall agentdebugx proofagent-harness" in readme
    assert "requires no code or configuration rollback" in readme
