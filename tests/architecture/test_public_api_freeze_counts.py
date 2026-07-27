"""Public API freeze counts (TD-R-07 / #6683)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "configs/quality/compatibility_facade_inventory.yaml"
SCORECARD = ROOT / "configs/quality/debt_scorecard.yaml"


def test_public_entrypoint_and_export_facade_counts_are_frozen() -> None:
    inv = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    scorecard = yaml.safe_load(SCORECARD.read_text(encoding="utf-8"))
    entrypoints = inv.get("retained_entrypoints") or []
    assert len(entrypoints) == 12
    governance = scorecard["sanctioned_public_entrypoint_governance"]["metrics"]
    assert governance["public_entrypoint_count"]["current_count"] == 12
    assert governance["public_export_facade_count"]["current_count"] == 4
    assert governance["public_export_facade_conflict_count"]["current_count"] == 0
    freeze = inv.get("retained_compatibility_freeze_policy") or {}
    assert freeze.get("status") == "active_no_growth"
    assert freeze.get("new_retained_surface_policy") == "blocked_without_public_api_decision"


def test_transition_debt_remains_empty_under_freeze() -> None:
    inv = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    assert inv.get("transition_debt") in ([], None)
