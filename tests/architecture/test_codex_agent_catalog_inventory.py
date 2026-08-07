# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Guard Codex agent catalog inventory against ORCHESTRATION drift."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / ".codex" / "agents"
ORCHESTRATION = AGENTS_DIR / "ORCHESTRATION.md"
README = AGENTS_DIR / "README.md"

ACTIVE_RUNTIME_PROFILES = frozenset(
    {
        "py-audit-bot",
        "py-config-bot",
        "py-debug-bot",
        "py-doc-bot",
        "py-plan-bot",
        "py-test-bot",
    }
)


pytestmark = pytest.mark.architecture


def test_tracked_py_agent_profiles_match_active_inventory() -> None:
    on_disk = {path.stem for path in AGENTS_DIR.glob("py-*.md") if path.is_file()}
    assert on_disk == ACTIVE_RUNTIME_PROFILES


def test_orchestration_mentions_every_active_profile() -> None:
    text = ORCHESTRATION.read_text(encoding="utf-8")
    for name in sorted(ACTIVE_RUNTIME_PROFILES):
        assert name in text, f"ORCHESTRATION.md missing active profile {name}"


def test_agent_readme_lists_six_active_and_marks_sp_docs_only() -> None:
    text = README.read_text(encoding="utf-8")
    assert "6 active" in text
    assert "docs-only" in text.lower() or "Docs-only" in text
    # No claim that sp-* are runtime agents under .codex/agents
    assert "Generic Utilities (12 agents)" not in text
    for name in sorted(ACTIVE_RUNTIME_PROFILES):
        assert f"`{name}`" in text
    # sp profiles must be labeled non-runtime
    assert re.search(r"sp-code-reviewer.*docs-only", text, re.I | re.S)
