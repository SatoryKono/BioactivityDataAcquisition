"""Architecture guardrails for closeout ratchet triage."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest
import yaml


pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRIAGE_PATH = PROJECT_ROOT / "configs" / "quality" / "closeout_ratchet_triage.yaml"
ARCHITECTURE_TESTS = PROJECT_ROOT / "tests" / "architecture"

ALLOWED_CLASSIFICATIONS = {
    "active_architecture_guard",
    "budget_closeout_ratchet",
    "live_inventory_ratchet",
    "transition_closeout_guard",
}


def _load_triage() -> dict[str, Any]:
    payload = yaml.safe_load(TRIAGE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def _triage_entries() -> list[dict[str, Any]]:
    payload = _load_triage()
    entries = payload.get("entries")
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) for entry in entries)
    return cast(list[dict[str, Any]], entries)


def _closeout_test_paths() -> set[str]:
    return {
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in ARCHITECTURE_TESTS.glob("*closeout*.py")
        if path.name != Path(__file__).name
    }


def test_closeout_ratchets_are_fully_classified() -> None:
    """Every executable closeout ratchet needs an explicit retention decision."""
    payload = _load_triage()
    assert payload["schema_version"] == 1
    assert payload["linked_issue"] == "#5931"
    assert payload["policy"]["max_unclassified_closeout_ratchets"] == 0

    classified_paths = {entry["path"] for entry in _triage_entries()}
    assert classified_paths == _closeout_test_paths()


def test_closeout_ratchet_entries_are_live_and_actionable() -> None:
    """Retained closeout tests must enforce live invariants, not stale history."""
    for entry in _triage_entries():
        assert entry["disposition"] == "retain_active"
        assert entry["classification"] in ALLOWED_CLASSIFICATIONS
        assert (PROJECT_ROOT / entry["path"]).is_file()
        assert isinstance(entry["live_guard"], str) and len(entry["live_guard"]) >= 20
        assert isinstance(entry["rationale"], str) and len(entry["rationale"]) >= 20


def test_closeout_ratchet_policy_does_not_allow_stale_historical_tests() -> None:
    """Historical-only closeout files should be removed or documented elsewhere."""
    policy = _load_triage()["policy"]
    assert policy["allowed_dispositions"] == ["retain_active"]
    assert "removed" not in policy["allowed_dispositions"]
    assert "historical_evidence" not in policy["allowed_classifications"]


def test_closeout_retention_summary_matches_live_inventory() -> None:
    """The tracked triage must summarize the live closeout inventory directly."""
    triage = _load_triage()
    entries = _triage_entries()
    classifications = Counter(entry["classification"] for entry in entries)

    assert triage["linked_issue"] == "#5931"
    assert triage["reviewed_on"] <= triage["review_by"]
    assert sum(classifications.values()) == len(_closeout_test_paths())
    assert set(classifications) == set(triage["policy"]["allowed_classifications"])
