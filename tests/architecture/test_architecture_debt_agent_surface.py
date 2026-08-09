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
"""Architecture guardrails for the audit-mode architecture-debt workflow."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CODEX_SKILL = ROOT / ".codex" / "skills" / "py-audit-bot" / "SKILL.md"
HISTORICAL_PROMPT_FILES = (
    ROOT
    / "docs"
    / "00-project"
    / "ai"
    / "prompts"
    / "architecture_metric_exemptions_tasks_json_prompt.md",
)


def test_architecture_debt_runtime_surfaces_exist() -> None:
    assert CODEX_SKILL.exists()
    assert (
        ROOT / "scripts" / "engineering" / "qa" / "generate_architecture_debt_tasks.py"
    ).exists()
    assert (
        ROOT / "scripts" / "engineering" / "qa" / "reduce_architecture_debt.py"
    ).exists()


def test_architecture_debt_audit_mode_is_self_contained() -> None:
    text = CODEX_SKILL.read_text(encoding="utf-8")
    assert "ai/claude/" not in text
    assert "Team orchestration" in text


def test_debt_mode_routes_config_writes_via_py_config_bot() -> None:
    text = CODEX_SKILL.read_text(encoding="utf-8")
    assert "debt" in text


def test_historical_prompts_reference_new_runtime_surface() -> None:
    for prompt_path in HISTORICAL_PROMPT_FILES:
        assert prompt_path.is_file(), f"tracked historical prompt is missing: {prompt_path}"
        text = prompt_path.read_text(encoding="utf-8")
        assert "py-audit-bot" in text
        assert "python -m scripts.engineering.qa generate-debt-tasks" in text
        assert "python -m scripts.engineering.qa reduce-architecture-debt" in text
