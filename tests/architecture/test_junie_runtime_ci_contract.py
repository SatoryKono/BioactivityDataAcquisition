"""CI linkage guards for the tracked Codex–Junie runtime parity contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "skills-consistency.yml"


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_skills_consistency_watches_runtime_parity_surfaces() -> None:
    workflow = _workflow()
    triggers = workflow[True]
    required = {
        ".codex/agents/**",
        ".codex/skills/**",
        ".junie/agents/**",
        ".junie/skills/**",
        "scripts/ai/junie/check_junie_mirror.sh",
        "scripts/ai/junie/junie-mirror-contract.json",
    }
    for event in ("push", "pull_request"):
        assert required <= set(triggers[event]["paths"])


def test_skills_consistency_executes_canonical_junie_checker() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    job = jobs["verify-codex-junie-runtime-parity"]
    commands = [step.get("run", "") for step in job["steps"] if isinstance(step, dict)]
    assert "bash scripts/ai/junie/check_junie_mirror.sh --check" in commands
