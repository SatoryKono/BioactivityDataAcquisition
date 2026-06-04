"""Contract guard: every shipped Gold entity has strict schema + registry evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.contracts import gold as gold_contracts
from tests.contract._gold_schema_snapshot_registry import (
    build_gold_schema_snapshot_registry,
    gold_schema_entities,
    load_gold_schema_snapshot_registry,
)

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_gold_exports_match_registry_entities() -> None:
    """All GoldSchema exports must be indexed in the snapshot registry."""
    assert set(gold_schema_entities()) == set(
        load_gold_schema_snapshot_registry()["entities"]
    )


@pytest.mark.parametrize("entity", sorted(gold_schema_entities()))
def test_each_gold_entity_is_strict_with_published_contract(entity: str) -> None:
    """Shipped Gold entities must use strict=True and publish contract JSON."""
    live = build_gold_schema_snapshot_registry()["entities"][entity]
    assert live["strict"] is True, f"{entity}: Gold schema must be strict=True"

    contract_path = ROOT / live["published_contract_path"]
    assert contract_path.exists(), (
        f"{entity}: missing published contract at {contract_path}"
    )


def test_gold_dq_bundles_cover_primary_entity_outputs() -> None:
    """DQ-sensitive bundles must reference entities present in the registry."""
    registry = load_gold_schema_snapshot_registry()
    entities = registry["entities"]
    for snapshot_name, meta in registry["dq_sensitive_outputs"].items():
        assert meta["entity"] in entities, (
            f"{snapshot_name}: entity {meta['entity']!r} missing from registry"
        )
        bundle_path = ROOT / meta["snapshot_path"]
        assert bundle_path.exists(), (
            f"{snapshot_name}: missing DQ bundle fixture {bundle_path}"
        )


def test_gold_contract_exports_are_schema_classes() -> None:
    """gold_contracts.__all__ must only expose GoldSchema DataFrameModel classes."""
    for export_name in gold_contracts.__all__:
        if not export_name.endswith("GoldSchema"):
            continue
        export_obj = getattr(gold_contracts, export_name)
        assert hasattr(export_obj, "to_schema"), (
            f"{export_name} must be a Pandera DataFrameModel"
        )
