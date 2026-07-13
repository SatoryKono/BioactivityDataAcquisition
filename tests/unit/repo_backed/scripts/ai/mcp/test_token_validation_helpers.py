"""Regression tests for MCP token validation helpers."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import pytest


# Skip bash-based tests on Windows; the checked-in shell helper is a repository
# contract, so this test belongs to the deterministic repo-backed unit lane.
pytestmark = [
    pytest.mark.unit,
    pytest.mark.repo_backed,
    pytest.mark.skipif(
        platform.system() == "Windows",
        reason="bash-based MCP token validation tests are not reliable on native Windows shells",
    ),
]

ROOT = Path(__file__).resolve().parents[6]
HELPER = ROOT / "scripts" / "ai" / "mcp" / "support" / "token_validation.sh"
NEO4J_WRAPPERS = [
    ROOT / "scripts" / "ai" / "mcp" / "mcp_neo4j_cypher_wrapper.sh",
    ROOT / "scripts" / "ai" / "mcp" / "mcp_neo4j_memory_wrapper.sh",
]


def _run_bash(
    script: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged_env = {
        key: value
        for key, value in os.environ.items()
        if not key.endswith("TOKEN") and "API_KEY" not in key and "PASSWORD" not in key
    }
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "-lc", script],
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_required_token_rejects_missing_value() -> None:
    result = _run_bash(
        f"source {HELPER}; mcp_validate_required_token TEST_TOKEN 20 'test MCP'"
    )

    assert result.returncode == 1
    assert "TEST_TOKEN is required for test MCP" in result.stderr
    assert "secret" not in result.stdout.lower()


def test_required_token_rejects_short_value_without_printing_secret() -> None:
    result = _run_bash(
        f"source {HELPER}; mcp_validate_required_token TEST_TOKEN 20 'test MCP'",
        env={"TEST_TOKEN": "short-secret"},
    )

    assert result.returncode == 1
    assert "too short" in result.stderr
    assert "short-secret" not in result.stderr


def test_required_token_accepts_standard_github_prefix() -> None:
    result = _run_bash(
        f"source {HELPER}; "
        "mcp_validate_required_token TEST_TOKEN 20 'GitHub MCP' "
        "'ghp_' 'github_pat_'",
        env={"TEST_TOKEN": "ghp_12345678901234567890"},
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_optional_token_warns_without_failing_when_absent() -> None:
    result = _run_bash(
        f"source {HELPER}; mcp_validate_optional_token OPTIONAL_TOKEN 20 'test MCP'"
    )

    assert result.returncode == 0
    assert "OPTIONAL_TOKEN is not set for test MCP" in result.stderr


def test_validate_only_exits_successfully() -> None:
    result = _run_bash(
        f"source {HELPER}; mcp_exit_if_validate_only 'demo'",
        env={"BIOETL_MCP_VALIDATE_ONLY": "1"},
    )

    assert result.returncode == 0
    assert "[OK] demo MCP wrapper validation completed" in result.stdout


@pytest.mark.parametrize("wrapper", NEO4J_WRAPPERS)
def test_neo4j_wrapper_validate_only_uses_local_defaults_without_auth(
    wrapper: Path,
) -> None:
    merged_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("NEO4J_")
        and not key.endswith("TOKEN")
        and "API_KEY" not in key
        and "PASSWORD" not in key
    }
    merged_env.update(
        {
            "BIOETL_MCP_VALIDATE_ONLY": "1",
            "BIOETL_REPO_ENV_LOADED": "1",
        }
    )

    result = subprocess.run(
        ["bash", str(wrapper)],
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "MCP wrapper validation completed" in result.stdout
