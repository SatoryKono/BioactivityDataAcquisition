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
    assert ".codex/agents/CODEX-RUNTIME.md" in mirror
    assert "does not redefine runtime behavior" in mirror
    assert "never increase debt" in mirror
