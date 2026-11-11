from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_codex_runtime_owns_task_routing_and_validation_matrix() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (root / ".codex" / "agents" / "CODEX-RUNTIME.md").read_text(
        encoding="utf-8"
    )
    mirror = (
        root
        / "docs"
        / "00-project"
        / "ai"
        / "agents"
        / "guides"
        / "CODEX_TASK_ROUTING.md"
    ).read_text(encoding="utf-8")

    for anchor in (
        "## Common Task Routing",
        "Diagnose without fixing",
        "Review the current diff",
        "## Risk-Based Validation",
        "V1",
        "V4",
        "debt outcome",
    ):
        assert anchor in runtime
    orchestration = (root / ".codex/agents/ORCHESTRATION.md").read_text(
        encoding="utf-8"
    )
    normalized_orchestration = " ".join(orchestration.split())
    assert "V1/V2 do not require a subagent chain" in normalized_orchestration
    assert (
        "V3/V4 retain orchestration and post-change validation"
        in normalized_orchestration
    )
    assert ".codex/agents/CODEX-RUNTIME.md" in mirror
    assert "does not redefine runtime behavior" in mirror
    assert "never increase debt" in mirror


@pytest.mark.parametrize("runtime", [".codex", ".junie", ".devin"])
def test_context_entrypoints_delegate_to_one_matrix(runtime: str) -> None:
    """Role entrypoints must not reintroduce their own bootstrap matrix."""
    root = Path(__file__).resolve().parents[2]
    name = {".codex": "CODEX", ".junie": "JUNIE", ".devin": "DEVIN"}[runtime]
    text = (root / runtime / "agents" / f"{name}-RUNTIME.md").read_text(
        encoding="utf-8"
    )
    section = text.split("## Context tiers", 1)[1].split("\n## ", 1)[0]
    normalized = " ".join(section.split())
    assert "single task-class matrix" in normalized
    assert "| Task class |" not in section
    assert "V3/V4 retain the full package and required pre-task" in normalized
    for relative in (
        "agents/ORCHESTRATION.md",
        "skills/py-audit-bot/references/wrapper-contract.md",
    ):
        guidance = " ".join(
            (root / runtime / relative).read_text(encoding="utf-8").split()
        )
        assert "single task-class matrix" in guidance
        assert "--skip-refresh-if-missing --skip-session-note" in guidance
        assert "authorized `read-write`" in guidance
        assert "PYTHONDONTWRITEBYTECODE=1" in guidance
        assert "DEGRADED" in guidance
        assert "already-read current sources" in guidance
        assert "1. Run the memory `post-task` workflow and report" not in guidance


def test_root_context_preserves_tiers_and_strict_no_write_controls() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative in ("AGENTS.md", ".junie/guidelines.md"):
        text = (root / relative).read_text(encoding="utf-8")
        assert "| V1 docs/prompt |" in text and "read-only optional" in text
        assert "| V2 focused code |" in text
        assert "| V3/V4 | full package:" in text
        assert "single task-class matrix" in text
        assert "PYTHONDONTWRITEBYTECODE=1" in text
        assert "--skip-refresh-if-missing --skip-session-note" in text
        assert (
            "a missing artifact or denied write capability does not lower the task tier"
            in text
        )
