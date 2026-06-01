"""Governance checks for UniProt semantic payload vocabulary inventory."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.extract_uniprot_semantic_payload_vocab import (
    extract_uniprot_semantic_payload_vocab,
)

pytestmark = pytest.mark.integration

INVENTORY_PATH = Path("configs/vocab/uniprot_semantic_payloads.yaml")


def test_uniprot_semantic_payload_inventory_covers_observed_fixture_values() -> None:
    payload = extract_uniprot_semantic_payload_vocab(
        [Path("tests/fixtures/bronze/uniprot/protein/sample_ci_2026-04-24.jsonl")]
    )
    inventory = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))

    for field_name, observed in payload.items():
        allowed = set(inventory["protein"][field_name])
        assert set(observed) <= allowed, (
            f"Unclassified UniProt semantic payload values for {field_name}: "
            f"{sorted(set(observed) - allowed)}"
        )
