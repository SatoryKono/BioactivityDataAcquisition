"""Architecture guardrails for the canonical architecture-debt workflow surface."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CODEX_SKILL = ROOT / ".codex" / "skills" / "py-architecture-debt-bot" / "SKILL.md"
CLAUDE_AGENT = ROOT / "ai" / "claude" / "agents" / "py-architecture-debt-bot.md"
SKILL_FILE = ROOT / "ai" / "claude" / "skills" / "py-architecture-debt-bot" / "SKILL.md"
PROMPT_FILES = (
    ROOT
    / "docs"
    / "00-project"
    / "ai"
    / "prompts"
    / "architecture_metric_exemptions_tasks_json_prompt.md",
    ROOT
    / "docs"
    / "00-project"
    / "ai"
    / "prompts"
    / "architecture_debt_reduction_orchestration.md",
)


def test_architecture_debt_runtime_surfaces_exist() -> None:
    assert CODEX_SKILL.exists()
    assert CLAUDE_AGENT.exists()
    assert SKILL_FILE.exists()
    assert (
        ROOT / "scripts" / "engineering" / "qa" / "generate_architecture_debt_tasks.py"
    ).exists()
    assert (
        ROOT / "scripts" / "engineering" / "qa" / "reduce_architecture_debt.py"
    ).exists()


def test_architecture_debt_codex_skill_is_self_contained() -> None:
    text = CODEX_SKILL.read_text(encoding="utf-8")
    assert "ai/claude/" not in text
    assert ".codex/agents/ORCHESTRATION.md" in text


def test_codex_agent_routes_config_writes_via_py_config_bot() -> None:
    text = CLAUDE_AGENT.read_text(encoding="utf-8")
    assert "configs/` меняет только `py-config-bot`" in text
    assert "py-config-bot" in text
    assert "generate-debt-tasks" in text
    assert "reduce-architecture-debt" in text


def test_historical_prompts_reference_new_runtime_surface() -> None:
    for prompt_path in PROMPT_FILES:
        text = prompt_path.read_text(encoding="utf-8")
        assert "py-architecture-debt-bot" in text
        assert "python -m scripts.engineering.qa generate-debt-tasks" in text
        assert "python -m scripts.engineering.qa reduce-architecture-debt" in text
