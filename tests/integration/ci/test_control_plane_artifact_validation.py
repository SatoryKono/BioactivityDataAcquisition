"""CI validation for committed control-plane artifact examples."""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.ci.validate_control_plane_artifacts import (
    validate_control_plane_artifacts,
)


ROOT = Path(__file__).resolve().parents[3]


def test_committed_control_plane_artifacts_match_published_contracts() -> None:
    """Committed examples must not drift from current control-plane contracts."""
    violations = validate_control_plane_artifacts(ROOT)
    assert violations == []
