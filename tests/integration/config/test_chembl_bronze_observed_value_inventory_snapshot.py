"""Snapshot tests for observed raw values extracted from tracked ChEMBL Bronze fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(".")
MANIFEST_PATH = ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
SNAPSHOT_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "normalization"
    / "chembl_bronze_observed_value_inventory_snapshot.json"
)

_FIELDS_BY_FIXTURE_KEY = {
    "chembl/assay": ("bao_format",),
    "chembl/cell_line": ("clo_id", "efo_id"),
    "chembl/tissue": ("bto_id", "efo_id", "uberon_id"),
}


def _load_manifest() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    fixtures = payload.get("fixtures")
    assert isinstance(fixtures, dict)
    return {
        str(key): value for key, value in fixtures.items() if isinstance(value, dict)
    }


def _iter_edge_fixture_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _build_inventory_snapshot() -> dict[str, object]:
    manifest = _load_manifest()
    fixtures: dict[str, object] = {}

    for fixture_key, field_names in sorted(_FIELDS_BY_FIXTURE_KEY.items()):
        entry = manifest[fixture_key]
        edge_fixtures = entry.get("edge_fixtures")
        assert isinstance(edge_fixtures, list) and edge_fixtures, (
            f"Missing tracked edge fixture for {fixture_key}"
        )
        for edge_fixture in edge_fixtures:
            assert isinstance(edge_fixture, dict)
            fixture_path = ROOT / str(edge_fixture["fixture_path"])
            rows = _iter_edge_fixture_rows(fixture_path)
            fixtures[f"{fixture_key}:{fixture_path.name}"] = {
                "pipeline": f"chembl_{fixture_key.split('/', maxsplit=1)[1]}",
                "fields": {
                    field_name: sorted(
                        {
                            str(row[field_name])
                            for row in rows
                            if row.get(field_name) not in (None, "")
                        }
                    )
                    for field_name in field_names
                },
            }

    return {"version": 1, "fixtures": fixtures}


@pytest.mark.integration
def test_tracked_chembl_bronze_observed_value_inventory_matches_snapshot() -> None:
    snapshot_payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert _build_inventory_snapshot() == snapshot_payload
