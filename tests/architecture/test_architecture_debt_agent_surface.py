"""Architecture guardrails for the canonical architecture-debt workflow surface."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CODEX_AGENT = ROOT / ".claude" / "agents" / "py-architecture-debt-bot.md"
CLAUDE_AGENT = ROOT / ".claude" / "agents" / "py-architecture-debt-bot.md"
SKILL_FILE = ROOT / ".claude" / "skills" / "py-architecture-debt-bot" / "SKILL.md"
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
    assert CODEX_AGENT.exists()
    assert CLAUDE_AGENT.exists()
    assert SKILL_FILE.exists()
    assert (
        ROOT / "scripts" / "engineering" / "qa" / "generate_architecture_debt_tasks.py"
    ).exists()
    assert (
        ROOT / "scripts" / "engineering" / "qa" / "reduce_architecture_debt.py"
    ).exists()


def test_architecture_debt_skill_points_to_claude_surface() -> None:
    text = SKILL_FILE.read_text(encoding="utf-8")
    assert ".claude/agents/py-architecture-debt-bot.md" in text
    assert ".codex/agents/py-architecture-debt-bot.md" not in text


def test_codex_agent_routes_config_writes_via_py_config_bot() -> None:
    text = CODEX_AGENT.read_text(encoding="utf-8")
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
