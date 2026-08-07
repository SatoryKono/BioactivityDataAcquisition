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

from pathlib import Path

import pytest

from scripts.ai.codex.native_runtime_contract import AGENT_NAMES

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / ".codex" / "agents"
ORCHESTRATION = AGENTS_DIR / "ORCHESTRATION.md"
README = AGENTS_DIR / "README.md"

ACTIVE_RUNTIME_PROFILES = frozenset(AGENT_NAMES)


pytestmark = pytest.mark.architecture


def test_tracked_py_agent_profiles_match_active_inventory() -> None:
    on_disk = {path.stem for path in AGENTS_DIR.glob("py-*.md") if path.is_file()}
    assert on_disk == ACTIVE_RUNTIME_PROFILES


def test_orchestration_mentions_every_active_profile() -> None:
    text = ORCHESTRATION.read_text(encoding="utf-8")
    for name in sorted(ACTIVE_RUNTIME_PROFILES):
        assert name in text, f"ORCHESTRATION.md missing active profile {name}"


def test_agent_readme_uses_the_canonical_active_inventory() -> None:
    text = README.read_text(encoding="utf-8")
    assert "## Active roles" in text
    assert "native_runtime_contract.py" in text
    for name in sorted(ACTIVE_RUNTIME_PROFILES):
        assert f"`{name}`" in text
    assert "sp-code-reviewer" not in text
