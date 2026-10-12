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
    """Runtime parity surfaces stay guarded after the coordinator cutover.

    Leaf Actions workflows no longer carry push/pull_request path filters;
    the CircleCI ``skills-consistency`` job runs the canonical mirror checks
    inside ``pr-gate`` on every gated run.
    """
    config = yaml.safe_load(
        (ROOT / ".circleci" / "config.yml").read_text(encoding="utf-8")
    )
    job = config["jobs"]["skills-consistency"]
    commands = " ".join(
        step["run"]["command"]
        for step in job["steps"]
        if isinstance(step, dict) and isinstance(step.get("run"), dict)
    )
    for check in (
        "bash scripts/ai/junie/check_junie_mirror.sh --check",
        "bash scripts/ops/support/skills/check_skills_mirror.sh --check",
        "bash scripts/ops/support/skills/check_ai_skills_layout.sh",
        "python -m scripts.ai.sync.runtime_skills",
    ):
        assert check in commands
    pr_gate_jobs = config["workflows"]["pr-gate"]["jobs"]
    assert any(
        isinstance(entry, dict) and "skills-consistency" in entry
        for entry in pr_gate_jobs
    )


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
    plan_texts = [
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".junie" / "plans").rglob("*.md"))
    ]
    for identifier in semantics["forbidden_identifiers"]:
        assert identifier not in runtime
        assert identifier not in guidelines
        for plan_text in plan_texts:
            assert identifier not in plan_text


def test_junie_guidelines_include_environment_configuration() -> None:
    """AGENTS.md and Junie guidelines must share the .env token contract (#9120)."""
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")
    for content in (agents, guidelines):
        assert "## Environment Configuration" in content
        assert "MUST use tokens and parameters from the repository root" in content


def test_junie_guidelines_include_full_tree_commits() -> None:
    """Junie Guardrails must mirror the full-tree commit gate (#11709/#11786)."""
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")
    assert "Full-tree commits only" in guidelines
    assert "check_no_partial_tree.py" in guidelines
