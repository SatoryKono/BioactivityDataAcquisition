"""Architecture guardrails for the behavior-retirement ledger."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "configs" / "quality" / "compatibility_sunset_ledger.yaml"


def _load_ledger() -> dict[str, object]:
    payload = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_behavior_retirement_ledger_exists_and_is_valid() -> None:
    """Ledger must exist and have valid structure."""
    assert LEDGER.exists(), "behavior retirement ledger must exist"

    payload = _load_ledger()
    assert payload["version"] == 1
    assert payload["policy_scope"] == "compatibility_behavior_sunset"
    assert isinstance(payload["entries"], list)


def test_behavior_retirement_ledger_entries_have_required_fields() -> None:
    """Each ledger entry must have required retirement criteria."""
    payload = _load_ledger()

    for entry in payload["entries"]:
        assert isinstance(entry, dict)
        assert "test_pattern" in entry
        assert "sunset_criteria" in entry
        assert "status" in entry
        assert "owner" in entry
        assert isinstance(entry["sunset_criteria"], list)
        assert entry["sunset_criteria"]
