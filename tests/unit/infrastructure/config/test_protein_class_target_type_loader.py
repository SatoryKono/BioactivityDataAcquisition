"""Tests for protein-class target-type mapping config loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.infrastructure.config.protein_class_target_type_loader import (
    ProteinClassTargetTypeMappingLoader,
)

pytestmark = pytest.mark.unit


def _write_asset(configs_root: Path, payload: dict[str, object]) -> None:
    asset_dir = configs_root / "enums"
    asset_dir.mkdir(parents=True)
    (asset_dir / "protein_class_l1_target_type.asset.v1.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_protein_class_target_type_mapping_loader_reads_json_asset(
    tmp_path: Path,
) -> None:
    _write_asset(
        tmp_path,
        {
            "mapping_version": "protein_class_l1_map_v1",
            "rows": [
                ["Enzyme", "enzyme", True],
                ["Unclassified protein", "unclassified_protein", False],
            ],
        },
    )

    data = ProteinClassTargetTypeMappingLoader(tmp_path).load()

    assert data.mapping_version == "protein_class_l1_map_v1"
    assert [entry.canonical_l1 for entry in data.entries] == [
        "enzyme",
        "unclassified_protein",
    ]
    assert [entry.counts_for_target_type for entry in data.entries] == [True, False]


def test_protein_class_target_type_mapping_loader_rejects_invalid_rows_payload(
    tmp_path: Path,
) -> None:
    _write_asset(tmp_path, {"mapping_version": "v1", "rows": {"bad": "shape"}})

    with pytest.raises(ValueError, match="Invalid protein class mapping asset"):
        ProteinClassTargetTypeMappingLoader(tmp_path).load()


def test_protein_class_target_type_mapping_loader_rejects_invalid_row_shape(
    tmp_path: Path,
) -> None:
    _write_asset(tmp_path, {"mapping_version": "v1", "rows": [["only", "two"]]})

    with pytest.raises(ValueError, match="arrays with 3\\+ columns"):
        ProteinClassTargetTypeMappingLoader(tmp_path).load()


def test_protein_class_target_type_mapping_loader_rejects_missing_mapping_version(
    tmp_path: Path,
) -> None:
    _write_asset(
        tmp_path, {"mapping_version": " ", "rows": [["Enzyme", "enzyme", True]]}
    )

    with pytest.raises(ValueError, match="missing mapping_version"):
        ProteinClassTargetTypeMappingLoader(tmp_path).load()
