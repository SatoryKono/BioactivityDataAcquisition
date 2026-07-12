"""Anti-drift checks for diagram narrative overview documents."""

from __future__ import annotations

import pytest

import re
from pathlib import Path


pytestmark = pytest.mark.architecture

REPO_ROOT = Path(__file__).resolve().parents[2]
CLASS_SUMMARY = (
    REPO_ROOT
    / "docs"
    / "02-architecture"
    / "diagrams"
    / "descriptions"
    / "class-summary.md"
)
ARCHITECTURE_REFERENCE = (
    REPO_ROOT
    / "docs"
    / "02-architecture"
    / "diagrams"
    / "guide"
    / "architecture-reference.md"
)
CURRENT_STATE_DIAGRAMS = (
    REPO_ROOT / "docs" / "02-architecture" / "current-state-diagrams.md"
)


def test_class_summary_is_explicitly_narrative_not_inventory() -> None:
    content = CLASS_SUMMARY.read_text(encoding="utf-8")

    assert "narrative-картой" in content
    assert "не является точным инвентарём" in content
    assert not re.search(r"примерно \d+ классов", content)


def test_architecture_reference_avoids_stale_inventory_labels() -> None:
    content = ARCHITECTURE_REFERENCE.read_text(encoding="utf-8")

    assert "26 Ports (Protocols):" not in content
    assert "9 Entities" not in content
    assert "11 Value Objects" not in content
    assert ".mermaid](../" not in content


def test_current_state_diagrams_embedded_blocks_are_marked_summary_only() -> None:
    lines = CURRENT_STATE_DIAGRAMS.read_text(encoding="utf-8").splitlines()
    unmarked: list[int] = []

    for idx, line in enumerate(lines):
        if line.strip() != "```mermaid":
            continue
        marker_window = "\n".join(lines[max(0, idx - 3) : idx])
        if (
            "diagram-audit:summary-only" not in marker_window
            and "diagram-audit:canonical-id=" not in marker_window
        ):
            unmarked.append(idx + 1)

    assert unmarked == []
