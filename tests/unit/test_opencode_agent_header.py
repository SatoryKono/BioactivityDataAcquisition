"""Drift check for the shared OpenCode agent header (#11705)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO_ROOT / ".opencode" / "agent"
CORE_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "opencode_header_core.txt"
)

AGENT_FILES = (
    "bugfix.md",
    "qa.md",
    "repo-agent.md",
    "review.md",
    "rfc.md",
    "stale.md",
    "triage.md",
)

# Per-agent tails: required additions on top of the shared core.
AGENT_TAILS = {
    "bugfix.md": "Phase 1 is read-only",
    "triage.md": "Never apply the reserved `agent-fix` label",
}


def _core() -> str:
    return CORE_FIXTURE.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", AGENT_FILES)
def test_agent_contains_canonical_core(name: str) -> None:
    text = (AGENT_DIR / name).read_text(encoding="utf-8")
    assert _core() in text, f"{name}: shared header core drifted"


@pytest.mark.parametrize("name, tail", sorted(AGENT_TAILS.items()))
def test_agent_keeps_required_tail(name: str, tail: str) -> None:
    text = (AGENT_DIR / name).read_text(encoding="utf-8")
    assert tail in text, f"{name}: required per-agent tail missing"
