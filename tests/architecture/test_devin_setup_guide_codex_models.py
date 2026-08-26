"""Devin setup guide must not assign Claude models to Codex (#9697)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

GUIDE = Path(".devin/agents/DEVIN-SETUP-GUIDE.md")


def test_devin_setup_guide_does_not_assign_opus_sonnet_to_codex() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "does not pin opus/sonnet" in text
    assert "Fixed per profile (opus/sonnet)" not in text
