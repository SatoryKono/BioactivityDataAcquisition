"""Bounded golden snapshots for DQ-sensitive Gold output bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.contract._gold_schema_snapshot_registry import (
    load_gold_schema_snapshot_registry,
)

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def _is_compatible_value(*, dtype: str, value: Any) -> bool:
    if dtype == "bool":
        return isinstance(value, bool)
    if dtype == "int64":
        return isinstance(value, int) and not isinstance(value, bool)
    if dtype == "float64":
        return (isinstance(value, float) or isinstance(value, int)) and not isinstance(
            value, bool
        )
    if dtype == "str":
        return isinstance(value, str)
    return False


@pytest.mark.parametrize(
    "snapshot_name",
    sorted(load_gold_schema_snapshot_registry()["dq_sensitive_outputs"]),
)
def test_gold_dq_snapshot_bundle_matches_registry(snapshot_name: str) -> None:
    registry = load_gold_schema_snapshot_registry()
    output_meta = registry["dq_sensitive_outputs"][snapshot_name]
    entity_meta = registry["entities"][output_meta["entity"]]

    snapshot_path = ROOT / output_meta["snapshot_path"]
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert payload["snapshot_name"] == snapshot_name
    assert payload["entity"] == output_meta["entity"]
    assert payload["bundle_columns"] == output_meta["required_columns"]

    rows = payload["rows"]
    assert isinstance(rows, list) and rows
    assert payload["row_count"] == len(rows)

    bundle_columns = output_meta["required_columns"]
    assert any(
        bool(row.get("_dq_warn")) or bool(row.get("_dq_error")) for row in rows
    ), f"{snapshot_name} must include at least one flagged DQ row"

    for column in bundle_columns:
        assert column in entity_meta["fields"], (
            f"{snapshot_name}: bundle column {column!r} is missing from the "
            f"{output_meta['entity']} schema snapshot"
        )

    for row in rows:
        assert set(row) == set(bundle_columns), (
            f"{snapshot_name}: row keys must exactly match bundle_columns"
        )
        for column in bundle_columns:
            field_meta = entity_meta["fields"][column]
            value = row[column]
            if value is None:
                assert field_meta["nullable"], (
                    f"{snapshot_name}: column {column!r} stores null in the bounded "
                    "snapshot but the Gold schema marks it non-nullable"
                )
                continue
            assert _is_compatible_value(dtype=field_meta["dtype"], value=value), (
                f"{snapshot_name}: column {column!r} expects {field_meta['dtype']!r}, "
                f"got value {value!r}"
            )
