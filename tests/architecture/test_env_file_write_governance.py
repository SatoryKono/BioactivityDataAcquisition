"""Regression checks for local env-file write governance."""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
OPT_IN = "BIOETL_CREATE_LOCAL_ENV_FILES"

ENV_WRITE_SURFACES = (
    "scripts/ai/codex/run-codex.sh",
    "scripts/ai/gemini/run-gemini.sh",
    "scripts/ai/codex/helper/setup-env.sh",
    "scripts/ai/gemini/helper/setup-env.sh",
    "scripts/ai/codex/helper/check-env.ps1",
    "scripts/ai/gemini/run-gemini-docker.ps1",
    "scripts/ai/vibe/helper/setup-env.sh",
    "scripts/memory/setup/wsl_startup.sh",
)


@pytest.mark.parametrize("relative_path", ENV_WRITE_SURFACES)
def test_env_file_writes_require_explicit_local_opt_in(relative_path: str) -> None:
    """Scripts that can write .env* files must expose an explicit opt-in gate."""
    text = (ROOT / relative_path).read_text(encoding="utf-8")

    assert OPT_IN in text, f"{relative_path} must gate .env writes with {OPT_IN}=1"
    assert (
        "without BIOETL_CREATE_LOCAL_ENV_FILES=1" in text
        or "rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1" in text
    ), (
        f"{relative_path} must document non-mutating default behavior"
    )


def test_memory_wsl_startup_does_not_upsert_env_local_without_opt_in() -> None:
    """Existing .env.local files are still machine-local and must not be mutated by default."""
    text = (ROOT / "scripts/memory/setup/wsl_startup.sh").read_text(encoding="utf-8")

    assert "ENV_FILE_WRITE_ALLOWED=0" in text
    assert 'if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" == "1" ]]; then' in text
    assert "if [[ ${ENV_FILE_WRITE_ALLOWED} -eq 1 ]]; then" in text
    assert text.index("if [[ ${ENV_FILE_WRITE_ALLOWED} -eq 1 ]]; then") < text.index(
        'upsert_env_local "$ENV_LOCAL" "NEO4J_URI"'
    )
