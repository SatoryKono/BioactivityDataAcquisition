# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for the normalization fallback inventory report."""

from __future__ import annotations

import pytest

import json
from pathlib import Path
from typing import cast

from scripts.engineering.qa.report_normalization_fallback_inventory import (
    _build_payload,
    _fallback_rows,
    _render_markdown,
    build_fallback_inventory_payload,
    main,
)


pytestmark = pytest.mark.unit


def test_fallback_rows_are_empty_when_all_entity_pipelines_are_profiled() -> None:
    rows = _fallback_rows()

    assert rows == []


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
        ],
        coverage_kpi={
            "surface": "entity_record",
            "name": "explicit_profile_coverage_pct",
            "numerator": 7,
            "denominator": 10,
            "value_pct": 70.0,
        },
        surface_kpis=[
            {
                "surface": "entity_record",
                "name": "explicit_profile_coverage_pct",
                "numerator": 7,
                "denominator": 10,
                "value_pct": 70.0,
                "description": "Entity coverage.",
            },
            {
                "surface": "composite_join_key",
                "name": "composite_join_key_policy_coverage_pct",
                "numerator": 4,
                "denominator": 4,
                "value_pct": 100.0,
                "description": "Composite coverage.",
            },
        ],
        semantic_invariants=[
            {
                "surface": "profile_semantics",
                "name": "shipped_profile_meta_passthrough_pct",
                "numerator": 10,
                "denominator": 10,
                "value_pct": 100.0,
                "description": "Meta passthrough contract.",
                "regressions": [],
            }
        ],
    )

    coverage_kpi = cast(dict[str, object], payload["coverage_kpi"])
    surface_kpis = cast(list[dict[str, object]], payload["surface_kpis"])
    semantic_invariants = cast(list[dict[str, object]], payload["semantic_invariants"])
    pipelines = cast(list[dict[str, object]], payload["pipelines"])
    normalizers = cast(list[dict[str, object]], payload["normalizers"])
    sources = cast(list[dict[str, object]], payload["sources"])

    assert payload["scope"] == "entity_record_fallback_only"
    assert coverage_kpi["name"] == "explicit_profile_coverage_pct"
    assert len(surface_kpis) == 2
    assert len(semantic_invariants) == 1
    assert payload["fallback_field_count"] == 3
    assert payload["fallback_business_field_count"] == 2
    assert payload["fallback_technical_passthrough_field_count"] == 1
    assert payload["pipelines_with_fallback_count"] == 1
    assert pipelines[0] == {
        "pipeline_name": "openalex_publication",
        "fallback_field_count": 3,
        "fallback_business_field_count": 2,
        "fallback_technical_passthrough_field_count": 1,
    }
    assert normalizers[0] == {
        "normalizer": "normalize_doi",
        "field_count": 1,
    }
    assert sources[0] == {
        "normalization_source": "fallback_business",
        "field_count": 2,
    }


def test_render_markdown_mentions_top_fallback_entries() -> None:
    markdown = _render_markdown(
        {
            "coverage_kpi": {
                "surface": "entity_record",
                "name": "explicit_profile_coverage_pct",
                "numerator": 7,
                "denominator": 10,
                "value_pct": 70.0,
            },
            "surface_kpis": [
                {
                    "surface": "entity_record",
                    "name": "explicit_profile_coverage_pct",
                    "numerator": 7,
                    "denominator": 10,
                    "value_pct": 70.0,
                    "description": "Entity coverage.",
                },
                {
                    "surface": "composite_join_key",
                    "name": "composite_join_key_policy_coverage_pct",
                    "numerator": 4,
                    "denominator": 4,
                    "value_pct": 100.0,
                    "description": "Composite coverage.",
                },
                {
                    "surface": "control_plane_reproducibility",
                    "name": "control_plane_normalization_coverage_pct",
                    "numerator": 6,
                    "denominator": 6,
                    "value_pct": 100.0,
                    "description": "Control-plane coverage.",
                },
            ],
            "semantic_invariants": [
                {
                    "surface": "profile_semantics",
                    "name": "shipped_profile_meta_passthrough_pct",
                    "numerator": 21,
                    "denominator": 21,
                    "value_pct": 100.0,
                    "description": "Meta passthrough contract.",
                    "regressions": [],
                }
            ],
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
            "pipelines": [
                {
                    "pipeline_name": "openalex_publication",
                    "fallback_field_count": 2,
                    "fallback_business_field_count": 1,
                    "fallback_technical_passthrough_field_count": 1,
                }
            ],
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
    assert "- scope: `entity_record_fallback_only`" in markdown
    assert (
        "Fallback inventory tracks only entity-record fallback normalization debt."
        in markdown
    )
    assert "## Surface Coverage Context" in markdown
    assert "## Semantic Invariant Context" in markdown
    assert (
        "- entity_record / explicit_profile_coverage_pct: `70.00%` (`7` / `10`)"
        in markdown
    )
    assert (
        "- profile_semantics / shipped_profile_meta_passthrough_pct: `100.00%` "
        "(`21` / `21`) Meta passthrough contract."
    ) in markdown
    assert (
        "- composite_join_key / composite_join_key_policy_coverage_pct: `100.00%` "
        "(`4` / `4`) Composite coverage."
    ) in markdown
    assert "`fallback_business` covers `1` fields" in markdown
    assert (
        "`openalex_publication` has `2` fallback fields "
        "(`fallback_business=1`, `fallback_technical_passthrough=1`)"
    ) in markdown
    assert (
        "`openalex_publication.title` -> `normalize_title` (`fallback_business`)"
        in markdown
    )


def test_main_writes_deterministic_artifacts(tmp_path: Path) -> None:
    json_out = tmp_path / "fallback.json"
    markdown_out = tmp_path / "fallback.md"

    assert (
        main(
            [
                "--limit",
                "5",
                "--json-out",
                str(json_out),
                "--markdown-out",
                str(markdown_out),
            ]
        )
        == 0
    )

    first_json = json_out.read_text(encoding="utf-8")
    first_md = markdown_out.read_text(encoding="utf-8")

    assert (
        main(
            [
                "--limit",
                "5",
                "--json-out",
                str(json_out),
                "--markdown-out",
                str(markdown_out),
            ]
        )
        == 0
    )

    assert json_out.read_text(encoding="utf-8") == first_json
    assert markdown_out.read_text(encoding="utf-8") == first_md
    assert json.loads(first_json)["mode"] == "report-only"
    assert json.loads(first_json)["scope"] == "entity_record_fallback_only"
    assert "semantic_invariants" in json.loads(first_json)


def test_main_returns_non_zero_when_fallback_business_budget_is_exceeded() -> None:
    current_budget = int(
        cast(int, build_fallback_inventory_payload()["fallback_business_field_count"])
    )
    assert main(["--max-fallback-business-fields", str(current_budget - 1)]) == 1


def test_main_accepts_current_fallback_business_budget() -> None:
    current_budget = str(
        cast(int, build_fallback_inventory_payload()["fallback_business_field_count"])
    )
    assert main(["--max-fallback-business-fields", current_budget]) == 0
