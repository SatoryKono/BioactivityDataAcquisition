"""Architecture tests for historical prompt surfaces using current docs-audit wording."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

HISTORICAL_PROMPT_FILES = (
    Path("docs/00-project/ai/prompts/documentation_diagrams_audit.md"),
    Path("docs/00-project/ai/prompts/refactor_orchestration_prompt.md"),
)


def test_historical_prompt_surfaces_do_not_reference_py_doc_swarm() -> None:
    for relative_path in HISTORICAL_PROMPT_FILES:
        text = relative_path.read_text(encoding="utf-8")
        assert "py-doc-swarm" not in text, (
            f"{relative_path} should use documentation-audit / "
            "documentation-cascade-audit wording"
        )
