"""#11133: ChEMBL integration diagram stays on public offset/limit flow."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DIAGRAM = (
    ROOT
    / "docs/02-architecture/diagrams/providers/chembl/01-api-integration-flow.mmd"
)
SVG = (
    ROOT
    / "docs/02-architecture/diagrams/providers/chembl/svg/01-api-integration-flow.svg"
)
DESCRIPTION = (
    ROOT
    / "docs/02-architecture/diagrams/descriptions/providers/chembl/01-api-integration-flow.md"
)
FORBIDDEN = (
    "API Key Available",
    "Configure API Key",
    "Cursor Pagination",
    "Scroll Pagination",
)


def test_chembl_integration_diagram_uses_public_offset_limit() -> None:
    sources = {
        DIAGRAM: DIAGRAM.read_text(encoding="utf-8"),
        SVG: SVG.read_text(encoding="utf-8"),
        DESCRIPTION: DESCRIPTION.read_text(encoding="utf-8"),
    }
    for path, text in sources.items():
        for label in FORBIDDEN:
            assert label not in text, f"{path.name} still contains {label}"
    diagram = sources[DIAGRAM]
    assert "Offset/Limit Pagination" in diagram
    assert "Public ChEMBL API" in diagram
    assert "Public ChEMBL" in sources[SVG]
