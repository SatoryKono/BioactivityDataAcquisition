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
