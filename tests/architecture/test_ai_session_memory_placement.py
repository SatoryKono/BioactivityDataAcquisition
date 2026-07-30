"""Placement guard for transient AI session memory."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DOCS_SESSION_ROOT = REPO_ROOT / "docs" / "00-project" / "ai" / "sessions"


def test_docs_mirror_contains_no_transient_session_state() -> None:
    """Keep generated task/session records inside canonical episodic retention."""
    tracked_candidates = (
        sorted(LEGACY_DOCS_SESSION_ROOT.rglob("*.md"))
        if LEGACY_DOCS_SESSION_ROOT.exists()
        else []
    )

    assert tracked_candidates == [], (
        "transient AI session records belong under src/memory/episodic, "
        f"not docs mirrors: {tracked_candidates}"
    )
