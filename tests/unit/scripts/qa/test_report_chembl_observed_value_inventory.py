"""Tests for the ChEMBL Bronze observed-value inventory report."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.engineering.qa.report_chembl_observed_value_inventory import (
    _render_markdown,
    build_inventory_payload,
    main,
)


def test_build_inventory_payload_covers_all_tracked_chembl_fixtures() -> None:
    payload = build_inventory_payload(max_examples=3)

    assert payload["source"] == "tracked_chembl_bronze_fixtures"
    assert payload["fixtures_count"] == 14
    assert payload["field_rows_count"] > 0

    fixture_keys = {fixture["fixture_key"] for fixture in payload["fixtures"]}
    assert fixture_keys == {
        "chembl/activity",
        "chembl/assay",
        "chembl/assay_parameters",
        "chembl/cell_line",
        "chembl/compound_record",
        "chembl/molecule",
        "chembl/protein_class",
        "chembl/publication",
        "chembl/publication_similarity",
        "chembl/publication_term",
        "chembl/subcellular_fraction",
        "chembl/target",
        "chembl/target_component",
        "chembl/tissue",
    }

    rows_by_pipeline = {
        pipeline_name: [
            row for row in payload["rows"] if row["pipeline_name"] == pipeline_name
        ]
        for pipeline_name in ("chembl_activity", "chembl_molecule")
    }
    assert len(rows_by_pipeline["chembl_activity"]) >= 11
    assert len(rows_by_pipeline["chembl_molecule"]) >= 24
    tracked_fixture_count_by_pipeline = {
        fixture["pipeline_name"]: fixture["tracked_fixture_count"]
        for fixture in payload["fixtures"]
        if fixture["pipeline_name"] in {"chembl_activity", "chembl_molecule"}
    }
    assert tracked_fixture_count_by_pipeline["chembl_activity"] == 2
    assert tracked_fixture_count_by_pipeline["chembl_molecule"] == 2


def test_render_markdown_mentions_fixture_and_field_counts() -> None:
    markdown = _render_markdown(
        {
            "source": "tracked_chembl_bronze_fixtures",
            "manifest_path": "configs/base/bronze_fixture_manifest.yaml",
            "fixtures_count": 2,
            "field_rows_count": 3,
            "fixtures": [
                {
                    "fixture_key": "chembl/activity",
                    "pipeline_name": "chembl_activity",
                    "fixture_path": "tests/fixtures/bronze/chembl/activity/sample_ci.jsonl",
                    "records": 20,
                    "field_count": 2,
                }
            ],
            "rows": [
                {
                    "pipeline_name": "chembl_activity",
                    "fixture_key": "chembl/activity",
                    "field_name": "standard_type",
                    "non_null_count": 20,
                    "null_count": 0,
                    "distinct_count": 3,
                    "observed_examples": ["IC50", "Ki"],
                    "fixture_path": "tests/fixtures/bronze/chembl/activity/sample_ci.jsonl",
                }
            ],
        },
        limit=5,
    )

    assert "# ChEMBL Bronze Observed Value Inventory" in markdown
    assert "- fixtures_count: `2`" in markdown
    assert "`chembl_activity.standard_type` distinct=`3`" in markdown


def test_main_writes_and_check_validates_deterministic_outputs(tmp_path: Path) -> None:
    json_out = tmp_path / "inventory.json"
    csv_out = tmp_path / "inventory.csv"
    markdown_out = tmp_path / "inventory.md"

    assert (
        main(
            [
                "--max-examples",
                "3",
                "--limit",
                "5",
                "--json-out",
                str(json_out),
                "--csv-out",
                str(csv_out),
                "--markdown-out",
                str(markdown_out),
            ]
        )
        == 0
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["fixtures_count"] == 14
    assert "pipeline_name,fixture_key,field_name" in csv_out.read_text(encoding="utf-8")
    assert "# ChEMBL Bronze Observed Value Inventory" in markdown_out.read_text(
        encoding="utf-8"
    )

    assert (
        main(
            [
                "--max-examples",
                "3",
                "--limit",
                "5",
                "--json-out",
                str(json_out),
                "--csv-out",
                str(csv_out),
                "--markdown-out",
                str(markdown_out),
                "--check",
            ]
        )
        == 0
    )
