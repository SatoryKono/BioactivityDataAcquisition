"""Tests for the governed ChEMBL observed vocabulary exporter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.data_quality.export_chembl_observed_vocab import (
    _render_csv,
    build_inventory_payload,
    main,
)


def test_build_inventory_payload_scans_all_tracked_chembl_pipelines() -> None:
    payload = build_inventory_payload()

    assert payload["source"] == "tracked_chembl_bronze_fixtures"
    assert len(payload["pipelines_scanned"]) == 14
    assert payload["governed_fields_count"] > 0
    assert payload["governed_fields_with_observations_count"] > 0
    assert payload["rows_count"] > 0


def test_render_csv_has_expected_header_order() -> None:
    csv_payload = _render_csv(
        [
            {
                "pipeline_name": "chembl_activity",
                "fixture_key": "chembl/activity",
                "field_name": "standard_units",
                "layer_hint": "bronze_fixture",
                "observed_value": "uM",
                "count": 3,
                "normalized_value": "µM",
                "classification_hint": "enum",
                "fixture_path": "tests/fixtures/bronze/chembl/activity/sample_ci.jsonl",
            }
        ]
    )

    assert csv_payload.startswith(
        "pipeline_name,fixture_key,field_name,layer_hint,observed_value,count,normalized_value,classification_hint,fixture_path\n"
    )


def test_main_writes_and_check_validates_outputs(tmp_path: Path) -> None:
    csv_out = tmp_path / "inventory.csv"
    json_out = tmp_path / "inventory.json"

    assert main(["--csv-out", str(csv_out), "--json-out", str(json_out)]) == 0

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["rows_count"] > 0
    assert payload["governed_fields_count"] > 0
    assert "classification_hint" in csv_out.read_text(encoding="utf-8")

    assert (
        main(
            [
                "--csv-out",
                str(csv_out),
                "--json-out",
                str(json_out),
                "--check",
            ]
        )
        == 0
    )


def test_missing_declared_fixture_path_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_manifest = tmp_path / "manifest.yaml"
    missing_manifest.write_text(
        "fixtures:\n  chembl/activity:\n    fixture_kind: tracked_ci_sample\n    fixture_path: tests/fixtures/bronze/chembl/activity/does_not_exist.jsonl\n",
        encoding="utf-8",
    )

    from scripts.data_quality import export_chembl_observed_vocab as module

    monkeypatch.setattr(module, "MANIFEST_PATH", missing_manifest)

    with pytest.raises(FileNotFoundError, match="does_not_exist.jsonl"):
        module.build_inventory_payload()
