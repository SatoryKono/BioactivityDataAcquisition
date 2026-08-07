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
