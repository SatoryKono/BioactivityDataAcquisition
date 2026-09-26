# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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


def test_gold_dq_bundle_policy_is_bounded_to_sensitive_outputs() -> None:
    """DQ bundle snapshots are required for the explicit DQ-sensitive subset."""
    registry = load_gold_schema_snapshot_registry()
    policy = registry["dq_bundle_policy"]
    entities = registry["entities"]
    dq_outputs = registry["dq_sensitive_outputs"]

    assert policy["scope"] == "dq_sensitive_outputs"
    assert policy["coverage_model"] == "bounded_subset"
    assert policy["all_gold_entities_required"] is False
    assert {meta["entity"] for meta in dq_outputs.values()} < set(entities)


def test_gold_contract_exports_are_schema_classes() -> None:
    """gold_contracts.__all__ must only expose GoldSchema DataFrameModel classes."""
    schema_exports = [
        name for name in gold_contracts.__all__ if name.endswith("GoldSchema")
    ]
    assert schema_exports, "gold_contracts must expose at least one Gold schema"
    for export_name in schema_exports:
        export_obj = getattr(gold_contracts, export_name)
        assert hasattr(export_obj, "to_schema"), (
            f"{export_name} must be a Pandera DataFrameModel"
        )
