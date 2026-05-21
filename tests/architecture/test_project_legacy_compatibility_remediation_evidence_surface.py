"""Governance checks for the legacy compatibility remediation evidence pack."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACK_ROOT = (
    ROOT
    / "docs"
    / "reports"
    / "evidence"
    / "project-legacy-compatibility-remediation"
)
CANONICAL_CROSS_SYNTHESIS = (
    PACK_ROOT
    / "03-synthesis"
    / "CROSS-SYNTHESIS-project-legacy-compatibility-remediation.md"
)


def test_canonical_cross_synthesis_is_readable() -> None:
    """The recovered parent synthesis must stay readable by normal tooling."""
    text = CANONICAL_CROSS_SYNTHESIS.read_text(encoding="utf-8")

    assert "Кросс-синтез: project-legacy-compatibility-remediation" in text
    assert "DEC-legacy-use-four-bucket-classification-instead-of-broad-purge" in text
    assert "retain-as-contract" in text
    assert "Wave 1" in text


def test_curated_evidence_surface_has_no_unreadable_visible_entries() -> None:
    """Visible curated evidence entries must keep working with standard stat calls."""
    pending = [PACK_ROOT]
    failures: list[str] = []

    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                try:
                    entry.stat(follow_symlinks=False)
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
                except OSError as exc:
                    failures.append(
                        f"{Path(entry.path).relative_to(ROOT)}: "
                        f"{type(exc).__name__} errno={getattr(exc, 'errno', None)} "
                        f"{exc}"
                    )

    if failures:
        pytest.fail(
            "Curated evidence surface has unreadable visible entries:\n"
            + "\n".join(f"  - {failure}" for failure in failures)
        )
