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
"""Architecture tests for historical prompt surfaces using current docs-audit wording."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

HISTORICAL_PROMPT_FILES = (
    Path(
        "docs/99-archive/prompts-2026-09/archive/campaigns/documentation_diagrams_audit.md"
    ),
    Path(
        "docs/99-archive/prompts-2026-09/archive/campaigns/refactor_orchestration_prompt.md"
    ),
)


def test_historical_prompt_surfaces_do_not_reference_py_doc_swarm() -> None:
    for relative_path in HISTORICAL_PROMPT_FILES:
        text = relative_path.read_text(encoding="utf-8")
        assert "py-doc-swarm" not in text, (
            f"{relative_path} should use documentation-audit / "
            "documentation-cascade-audit wording"
        )
