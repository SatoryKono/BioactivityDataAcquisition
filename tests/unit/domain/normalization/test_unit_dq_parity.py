"""Parity checks for canonical unit normalization and ChEMBL DQ configs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.normalization.chembl import normalize_standard_unit
from bioetl.domain.normalization.rules import UNIT_MAPPING, normalize_unit

ACTIVITY_CONFIG_PATH = Path("configs/entities/chembl/activity.yaml")
CHEMBL_STANDARD_UNIT_ALIAS_CASES = (
    ("uM", "µM"),
    ("UM", "µM"),
    ("μM", "µM"),
    ("µM", "µM"),
    ("micromolar", "µM"),
    ("nM", "nM"),
    ("NM", "nM"),
    ("nanomolar", "nM"),
    ("pM", "pM"),
    ("PM", "pM"),
    ("picomolar", "pM"),
    ("fM", "fM"),
    ("FM", "fM"),
    ("femtomolar", "fM"),
    ("mM", "mM"),
    ("MM", "mM"),
    ("millimolar", "mM"),
    ("M", "M"),
    ("m", "M"),
    ("molar", "M"),
    ("%", "%"),
    ("percent", "%"),
    ("PERCENT", "%"),
    ("percentage", "%"),
)


def _load_activity_config() -> dict[str, Any]:
    loaded = yaml.safe_load(ACTIVITY_CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _allowed_units(config: dict[str, Any]) -> frozenset[str]:
    for validation in config["quality"]["entity_field_validations"]:
        if validation.get("field") == "standard_units":
            return frozenset(validation["allowed"])
    raise AssertionError("standard_units validation is missing")


def test_common_micro_unit_aliases_normalize_to_canonical_allowed_unit() -> None:
    allowed_units = _allowed_units(_load_activity_config())

    for raw_value, expected in CHEMBL_STANDARD_UNIT_ALIAS_CASES:
        assert normalize_standard_unit(raw_value) == expected
        assert normalize_unit(raw_value) == expected
    assert normalize_unit(" µM ") in allowed_units
    assert normalize_unit(" percent ") in allowed_units


def test_activity_dq_allowed_units_are_stable_under_unit_normalization() -> None:
    allowed_units = _allowed_units(_load_activity_config())

    assert "uM" not in allowed_units
    assert "µM" in allowed_units
    assert {normalize_unit(unit) for unit in allowed_units} == set(allowed_units)


def test_generic_unit_normalizer_delegates_chembl_standard_unit_aliases() -> None:
    for raw_value, _expected in CHEMBL_STANDARD_UNIT_ALIAS_CASES:
        assert normalize_unit(raw_value) == normalize_standard_unit(raw_value)


def test_generic_unit_mapping_does_not_duplicate_chembl_standard_unit_aliases() -> None:
    chembl_specific_aliases = {
        raw_value for raw_value, _ in CHEMBL_STANDARD_UNIT_ALIAS_CASES
    }

    assert chembl_specific_aliases.isdisjoint(UNIT_MAPPING)
