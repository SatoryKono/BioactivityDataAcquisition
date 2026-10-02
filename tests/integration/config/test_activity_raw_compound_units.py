"""Raw provider unit expressions must not be confused with standard unit codes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize(
    "value,valid",
    [
        ("nM l-1", True),
        ("nM", True),
        ("mg/ml", True),
        ("nM; DROP", False),
        ("nM\nl-1", False),
    ],
)
def test_activity_raw_compound_unit_contract(value: str, valid: bool) -> None:
    root = Path(__file__).resolve().parents[3]
    payload = yaml.safe_load(
        (root / "configs/entities/chembl/activity.yaml").read_text(encoding="utf-8")
    )
    rules = payload["quality"]["entity_field_validations"]
    raw = next(rule for rule in rules if rule["field"] == "units")
    standard = next(rule for rule in rules if rule["field"] == "standard_units")
    assert bool(re.fullmatch(raw["pattern"], value)) is valid
    assert "nM l-1" not in standard["allowed"]
