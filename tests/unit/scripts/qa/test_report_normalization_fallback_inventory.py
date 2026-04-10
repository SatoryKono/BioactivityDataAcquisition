"""Tests for the normalization fallback inventory report."""

from __future__ import annotations

import json

from scripts.qa.report_normalization_fallback_inventory import (
    _build_payload,
    _fallback_rows,
    _render_markdown,
    main,
)


def test_fallback_rows_include_unprofiled_entity_fields() -> None:
    rows = _fallback_rows()

    assert any(
        row["pipeline_name"] == "openalex_publication"
        and row["field_name"] == "title"
        and row["normalization_source"] == "fallback_business"
        for row in rows
    )
    assert any(
        row["pipeline_name"] == "openalex_publication"
        and row["field_name"] == "_run_id"
        and row["normalization_source"] == "fallback_technical_passthrough"
        for row in rows
    )


def test_build_payload_summarizes_fallback_rows() -> None:
    payload = _build_payload(
        [
            {
                "pipeline_name": "openalex_publication",
                "field_name": "title",
                "normalizer": "normalize_title",
                "normalization_source": "fallback_business",
            },
            {
                "pipeline_name": "openalex_publication",
                "field_name": "doi",
                "normalizer": "normalize_doi",
                "normalization_source": "fallback_business",
            },
            {
                "pipeline_name": "openalex_publication",
                "field_name": "_run_id",
                "normalizer": "passthrough",
                "normalization_source": "fallback_technical_passthrough",
            },
        ]
    )

    assert payload["fallback_field_count"] == 3
    assert payload["fallback_business_field_count"] == 2
    assert payload["fallback_technical_passthrough_field_count"] == 1
    assert payload["pipelines_with_fallback_count"] == 1
    assert payload["pipelines"][0] == {
        "pipeline_name": "openalex_publication",
        "fallback_field_count": 3,
    }
    assert payload["normalizers"][0] == {
        "normalizer": "normalize_doi",
        "field_count": 1,
    }
    assert payload["sources"][0] == {
        "normalization_source": "fallback_business",
        "field_count": 2,
    }


def test_render_markdown_mentions_top_fallback_entries() -> None:
    markdown = _render_markdown(
        {
            "fallback_field_count": 2,
            "fallback_business_field_count": 1,
            "fallback_technical_passthrough_field_count": 1,
            "pipelines_with_fallback_count": 1,
            "sources": [
                {
                    "normalization_source": "fallback_business",
                    "field_count": 1,
                },
                {
                    "normalization_source": "fallback_technical_passthrough",
                    "field_count": 1,
                },
            ],
            "pipelines": [{"pipeline_name": "openalex_publication", "fallback_field_count": 2}],
            "normalizers": [
                {"normalizer": "normalize_title", "field_count": 1},
                {"normalizer": "passthrough", "field_count": 1},
            ],
            "entries": [
                {
                    "pipeline_name": "openalex_publication",
                    "field_name": "title",
                    "normalizer": "normalize_title",
                    "normalization_source": "fallback_business",
                }
            ],
        },
        limit=5,
    )

    assert "# Normalization Fallback Inventory" in markdown
    assert "`fallback_business` covers `1` fields" in markdown
    assert "`openalex_publication` has `2` fallback fields" in markdown
    assert (
        "`openalex_publication.title` -> `normalize_title` (`fallback_business`)"
        in markdown
    )


def test_main_writes_deterministic_artifacts(tmp_path) -> None:
    json_out = tmp_path / "fallback.json"
    markdown_out = tmp_path / "fallback.md"

    assert main(
        [
            "--limit",
            "5",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    ) == 0

    first_json = json_out.read_text(encoding="utf-8")
    first_md = markdown_out.read_text(encoding="utf-8")

    assert main(
        [
            "--limit",
            "5",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    ) == 0

    assert json_out.read_text(encoding="utf-8") == first_json
    assert markdown_out.read_text(encoding="utf-8") == first_md
    assert json.loads(first_json)["mode"] == "report-only"
