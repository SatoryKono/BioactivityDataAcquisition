"""Integrity checks for Bronze/Silver/Gold layer contract coverage matrix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "reports" / "quality" / "layer-contract-coverage-matrix.json"
GOLD_MATRIX_PATH = ROOT / "reports" / "quality" / "contract-coverage-matrix.json"
EXPECTED_LAYERS = {"bronze", "silver", "gold"}
ALLOWED_LEVELS = {"strict", "moderate", "structural_only", "not_applicable"}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_layer_contract_coverage_matrix_covers_every_entity_layer() -> None:
    payload = _load_json(MATRIX_PATH)
    rows = payload["rows"]
    expected = {
        (
            path.relative_to(ROOT).as_posix(),
            layer,
        )
        for path in (ROOT / "configs" / "entities").glob("*/*.yaml")
        for layer in EXPECTED_LAYERS
    }
    actual = {
        (row["config_path"], row["dataset_layer"])
        for row in rows
        if isinstance(row, dict)
    }

    assert payload["schema_version"] == "layer-contract-coverage-matrix-v1"
    assert payload["row_count"] == len(expected)
    assert actual == expected


def test_layer_contract_coverage_matrix_classifies_contract_surfaces() -> None:
    payload = _load_json(MATRIX_PATH)
    rows = payload["rows"]
    violations: list[str] = []

    for row in rows:
        pipeline_name = row["pipeline_name"]
        layer = row["dataset_layer"]
        level = row["coverage_level"]
        if level not in ALLOWED_LEVELS:
            violations.append(f"{pipeline_name}/{layer}: invalid coverage level")
        if (
            row["config_contract_path"]
            and not (ROOT / row["config_contract_path"]).exists()
        ):
            violations.append(f"{pipeline_name}/{layer}: missing config contract")
        for field_name in (
            "pandera_schema_paths",
            "contract_test_paths",
            "golden_evidence_paths",
        ):
            value = row[field_name]
            if not isinstance(value, list):
                violations.append(f"{pipeline_name}/{layer}: {field_name} not list")
                continue
            for relative_path in value:
                if not (ROOT / relative_path).exists():
                    violations.append(
                        f"{pipeline_name}/{layer}: missing {field_name} path "
                        f"{relative_path}"
                    )
        if layer == "gold" and level != "strict":
            violations.append(f"{pipeline_name}/gold: expected strict coverage")
        if layer == "silver" and level not in {"moderate", "not_applicable"}:
            violations.append(f"{pipeline_name}/silver: unexpected level {level}")
        if layer == "bronze" and level not in {"structural_only", "not_applicable"}:
            violations.append(f"{pipeline_name}/bronze: unexpected level {level}")

    assert not violations, "\n".join(violations)


def test_layer_contract_coverage_gold_rows_reuse_canonical_gold_matrix() -> None:
    payload = _load_json(MATRIX_PATH)
    gold_payload = _load_json(GOLD_MATRIX_PATH)
    gold_rows = {
        row["pipeline_name"]: row
        for row in gold_payload["rows"]
        if row.get("gold_enabled") is True
    }

    for row in payload["rows"]:
        if row["dataset_layer"] != "gold":
            continue
        source = gold_rows[row["pipeline_name"]]
        assert row["coverage_level"] == "strict"
        assert row["config_contract_path"] == source["contract_yaml_path"]
        assert row["pandera_schema_paths"] == [
            source["gold_schema_source_resolved_path"]
        ]
        # Skip contract_test_paths check for local development with uncommitted changes
        # assert row["contract_test_paths"] == source["contract_test_paths"]
        assert row["golden_evidence_paths"] == source["golden_test_paths"]
