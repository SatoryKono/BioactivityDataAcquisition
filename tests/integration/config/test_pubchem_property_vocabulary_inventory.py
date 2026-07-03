"""Governance checks for PubChem raw property-URN inventory."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.extract_pubchem_property_vocab import (
    extract_pubchem_property_vocab,
)

pytestmark = pytest.mark.integration

INVENTORY_PATH = Path("configs/vocab/pubchem_property_urn.yaml")


def test_pubchem_property_urn_inventory_covers_observed_fixture_values() -> None:
    payload = extract_pubchem_property_vocab(
        [
            Path("tests/fixtures/bronze/pubchem/compound/sample_ci_2026-04-24.jsonl"),
            Path(
                "tests/fixtures/bronze/pubchem/compound/sample_edge_property_vocab_2026-05-05.jsonl"
            ),
        ]
    )
    inventory = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))

    for field_name, observed in payload.items():
        allowed = set(inventory["fields"][field_name]["values"])
        assert set(observed) <= allowed, (
            f"Unclassified PubChem property URN values for {field_name}: "
            f"{sorted(set(observed) - allowed)}"
        )
