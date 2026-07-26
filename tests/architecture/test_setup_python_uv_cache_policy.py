"""Architecture guardrails for the shared setup-python-uv cache contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
ACTION_PATH = ROOT / ".github" / "actions" / "setup-python-uv" / "action.yml"
TEST_OPTIMIZATION_GUIDE = ROOT / "docs" / "03-guides" / "test-optimization-guide.md"


def _load_action() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(ACTION_PATH.read_text(encoding="utf-8")))


def _step_by_name(name: str) -> dict[str, Any]:
    action = _load_action()
    steps = cast(list[dict[str, Any]], cast(dict[str, Any], action["runs"])["steps"])
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"setup-python-uv action is missing step {name!r}")


def test_environment_cache_fingerprint_includes_all_environment_inputs() -> None:
    step = _step_by_name("Compute environment cache fingerprint")
    script = cast(str, step["run"])

    assert step["id"] == "environment-cache"
    for token in (
        "INPUT_PYTHON_VERSION",
        "INPUT_UV_EXTRAS",
        "INPUT_UV_SYNC_ARGS",
        "uv.lock",
        "pyproject.toml",
        ".github/actions/setup-python-uv/action.yml",
        "sha256sum",
        "GITHUB_OUTPUT",
    ):
        assert token in script


def test_uv_virtualenv_cache_uses_environment_fingerprint_not_only_lockfile() -> None:
    step = _step_by_name("Cache uv and virtualenv")
    with_block = cast(dict[str, str], step["with"])

    assert "steps.environment-cache.outputs.python-fragment" in with_block["key"]
    assert "steps.environment-cache.outputs.fingerprint" in with_block["key"]
    assert "hashFiles('uv.lock')" not in with_block["key"]
    assert (
        "steps.environment-cache.outputs.python-fragment" in with_block["restore-keys"]
    )


def test_pytest_cache_remains_separate_from_environment_cache_fingerprint() -> None:
    step = _step_by_name("Cache pytest and hypothesis")
    with_block = cast(dict[str, str], step["with"])

    assert "inputs.pytest-cache-prefix" in with_block["key"]
    assert "inputs.pytest-cache-fingerprint" in with_block["key"]
    assert "hashFiles('tests/**/*.py')" in with_block["key"]
    assert "environment-cache" not in with_block["key"]


def test_uv_run_steps_reuse_the_environment_synced_by_the_action() -> None:
    step = _step_by_name(
        "Pin locked/no-build/no-sync defaults for subsequent uv run steps"
    )
    script = cast(str, step["run"])

    assert 'echo "UV_FROZEN=1"' in script
    assert 'echo "UV_NO_BUILD=1"' in script
    assert 'echo "UV_NO_SYNC=1"' in script


def test_ci_cache_contract_is_documented_for_contributors() -> None:
    text = TEST_OPTIMIZATION_GUIDE.read_text(encoding="utf-8")

    for token in (
        "setup-python-uv",
        "uv.lock",
        "pyproject.toml",
        "uv-extras",
        "uv-sync-args",
        "pytest cache",
        "UV_NO_SYNC",
    ):
        assert token in text
