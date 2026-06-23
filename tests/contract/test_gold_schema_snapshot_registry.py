"""Registry-driven Gold schema snapshot drift checks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.contract._gold_schema_snapshot_registry import (
    assert_gold_schema_entity_matches_snapshot,
    assert_gold_schema_snapshot_registry_shape,
    gold_schema_entities,
    load_gold_schema_snapshot_registry,
)

UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
ROOT = Path(__file__).resolve().parents[2]

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_gold_schema_snapshot_registry_shape() -> None:
    snapshot = load_gold_schema_snapshot_registry()
    assert_gold_schema_snapshot_registry_shape(snapshot)
    assert set(snapshot["entities"]) == set(gold_schema_entities())


@pytest.mark.parametrize("entity", sorted(gold_schema_entities()))
def test_gold_schema_entity_matches_snapshot(entity: str) -> None:
    assert_gold_schema_entity_matches_snapshot(
        entity,
        update_snapshots=UPDATE_SNAPSHOTS,
    )


@pytest.mark.parametrize("entity", sorted(gold_schema_entities()))
def test_gold_schema_registry_published_contract_path_exists(entity: str) -> None:
    snapshot = load_gold_schema_snapshot_registry()
    contract_path = ROOT / snapshot["entities"][entity]["published_contract_path"]
    assert contract_path.exists(), f"Missing published Gold contract: {contract_path}"
