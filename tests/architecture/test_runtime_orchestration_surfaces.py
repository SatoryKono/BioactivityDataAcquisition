"""Architecture tests for active runtime orchestration surface wording."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

ACTIVE_RUNTIME_ORCHESTRATION_FILES = (
    Path(".codex/agents/ORCHESTRATION.md"),
    Path(".codex/agents/CODEX-RUNTIME.md"),
)


def test_active_runtime_orchestration_surfaces_do_not_reference_py_doc_swarm() -> None:
    for relative_path in ACTIVE_RUNTIME_ORCHESTRATION_FILES:
        text = relative_path.read_text(encoding="utf-8")
        assert "py-doc-swarm" not in text, (
            f"{relative_path} should use current docs-audit surfaces instead of "
            "legacy docs-swarm references"
        )
