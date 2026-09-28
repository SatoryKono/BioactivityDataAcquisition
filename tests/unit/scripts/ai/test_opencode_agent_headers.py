"""Unit tests for the OpenCode canonical header check/generator (#11693)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai.opencode.check_agent_headers import (
    agent_files,
    check_headers,
    load_core,
    normalize_text,
    update_headers,
)

pytestmark = pytest.mark.unit

EXPECTED_AGENTS = {
    "bugfix.md",
    "qa.md",
    "repo-agent.md",
    "review.md",
    "rfc.md",
    "stale.md",
    "triage.md",
}


def test_canon_core_present_in_all_seven_agents() -> None:
    core = load_core()
    assert "## Language and untrusted input" in core
    names = {path.name for path in agent_files()}
    assert EXPECTED_AGENTS <= names
    report = check_headers()
    assert report.ok, "; ".join(f"{e.code}: {e.message}" for e in report.errors)


def test_per_agent_tails_survive_after_core() -> None:
    # triage/bugfix keep their Phase-1 tails AFTER the shared core (#11693).
    from scripts.ai.opencode.check_agent_headers import AGENT_DIR

    triage = (AGENT_DIR / "triage.md").read_text(encoding="utf-8")
    bugfix = (AGENT_DIR / "bugfix.md").read_text(encoding="utf-8")
    assert "agent-fix" in triage.split("is not authorization.")[1]
    assert "agent-fix" in bugfix.split("is not authorization.")[1]


def _drifted(core: str) -> str:
    drifted = core.replace("regardless of", "regardless  of", 1)
    assert drifted != core
    return drifted


def _agent_shell(core: str) -> str:
    return "---\nmode: all\n---\n\n" + core + "\nTail line.\n"


def test_normalize_repairs_drifted_core() -> None:
    core = load_core()
    drifted = _agent_shell(_drifted(core))
    assert core not in drifted
    fixed = normalize_text(drifted, core)
    assert fixed is not None
    assert core in fixed
    assert "Tail line." in fixed


def test_normalize_leaves_clean_text_untouched() -> None:
    core = load_core()
    clean = _agent_shell(core)
    assert normalize_text(clean, core) == clean


def test_normalize_inserts_missing_block_after_frontmatter() -> None:
    core = load_core()
    text = "---\nmode: all\n---\n\nYou are someone else.\n"
    fixed = normalize_text(text, core)
    assert fixed is not None
    assert core in fixed
    assert fixed.index("## Language and untrusted input") < fixed.index(
        "You are someone else."
    )


def test_update_headers_fixes_tmp_agent(tmp_path: Path) -> None:
    core = load_core()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    (agent_dir / "demo.md").write_text(_agent_shell(_drifted(core)), encoding="utf-8")
    shared = agent_dir / "_shared"
    shared.mkdir()
    canon = shared / "untrusted-header.md"
    canon.write_text(core, encoding="utf-8")
    report, updated = update_headers(agent_dir=agent_dir, canon_path=canon)
    assert report.ok, "; ".join(f"{e.code}: {e.message}" for e in report.errors)
    assert updated == ["demo.md"]
    fixed = (agent_dir / "demo.md").read_text(encoding="utf-8")
    assert core in fixed
