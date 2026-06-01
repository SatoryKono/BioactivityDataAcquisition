"""Architecture tests for active internal orchestration docs wording."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

ACTIVE_ORCHESTRATION_DOCS = (
    Path("docs/00-project/ai/agents/agents/ORCHESTRATION.md"),
    Path("docs/00-project/ai/agents/agents/README.md"),
    Path("docs/00-project/ai/agents/policy/agent-orchestration-rules.md"),
)


def test_active_internal_orchestration_docs_do_not_reference_py_doc_swarm() -> None:
    for relative_path in ACTIVE_ORCHESTRATION_DOCS:
        text = relative_path.read_text(encoding="utf-8")
        assert "py-doc-swarm" not in text, (
            f"{relative_path} should use current docs-audit surfaces instead of "
            "legacy docs-swarm references"
        )
