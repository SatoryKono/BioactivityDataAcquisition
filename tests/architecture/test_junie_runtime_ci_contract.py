"""CI linkage guards for the tracked Codex–Junie runtime parity contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "skills-consistency.yml"
CONTRACT_PATH = ROOT / "scripts" / "ai" / "junie" / "junie-mirror-contract.json"
JUNIE_RUNTIME_PATH = ROOT / ".junie" / "agents" / "JUNIE-RUNTIME.md"
JUNIE_GUIDELINES_PATH = ROOT / ".junie" / "guidelines.md"


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
        "scripts/ai/junie/check_junie_mirror.py",
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


def test_junie_runtime_maps_exact_codex_profile_inventory() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    excluded = set(contract["parity_scope"]["agents"]["exclude_filenames"])
    expected = {
        path.stem
        for path in (ROOT / ".codex" / "agents").glob("py-*.md")
        if path.name not in excluded
    }
    runtime = JUNIE_RUNTIME_PATH.read_text(encoding="utf-8")
    mapped = set(
        re.findall(r"^\|\s*`(py-[a-z0-9-]+)`\s*\|", runtime, flags=re.MULTILINE)
    )

    assert mapped == expected


def test_junie_dashboard_routing_uses_active_observability_skills() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    semantics = contract["runtime_semantics"]
    runtime = JUNIE_RUNTIME_PATH.read_text(encoding="utf-8")
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")

    for skill_name in semantics["required_dashboard_skills"]:
        assert f".junie/skills/{skill_name}/" in guidelines
    for identifier in semantics["forbidden_identifiers"]:
        assert identifier not in runtime
        assert identifier not in guidelines


def test_junie_guidelines_include_environment_configuration() -> None:
    """AGENTS.md and Junie guidelines must share the .env token contract (#9120)."""
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")
    for content in (agents, guidelines):
        assert "## Environment Configuration" in content
        assert "MUST use tokens and parameters from the repository root" in content
