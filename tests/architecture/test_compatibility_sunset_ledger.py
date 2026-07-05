"""Architecture guardrails for compatibility behavior test sunset ledger."""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SUNSET_LEDGER = ROOT / "configs" / "quality" / "compatibility_sunset_ledger.yaml"


@pytest.mark.architecture
def test_compatibility_sunset_ledger_exists_and_is_valid() -> None:
    """Sunset ledger must exist and have valid structure."""
    assert SUNSET_LEDGER.exists(), "Compatibility sunset ledger must exist"
    
    payload = yaml.safe_load(SUNSET_LEDGER.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload["version"] == 1
    assert payload["policy_scope"] == "compatibility_behavior_sunset"
    assert "entries" in payload
    assert isinstance(payload["entries"], list)


@pytest.mark.architecture
def test_compatibility_sunset_ledger_has_required_fields() -> None:
    """Each ledger entry must have required sunset criteria."""
    payload = yaml.safe_load(SUNSET_LEDGER.read_text(encoding="utf-8"))
    
    for entry in payload["entries"]:
        assert "test_pattern" in entry
        assert "sunset_criteria" in entry
        assert "status" in entry
        assert "owner" in entry
        assert isinstance(entry["sunset_criteria"], list)
        assert len(entry["sunset_criteria"]) > 0
