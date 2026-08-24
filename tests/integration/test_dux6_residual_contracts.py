"""DUX6 residual readability contracts (post-DUX5 re-audit)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "grafana" / "dashboards"
DOCS = ROOT / "docs" / "03-guides" / "dashboards"
AUDIT_PROTOCOLS = DOCS / "archive" / "audit-protocols"

pytestmark = pytest.mark.integration


def _walk(panels: list[dict[str, Any]] | None):
    for panel in panels or []:
        yield panel
        yield from _walk(panel.get("panels"))


def test_dux6_docs_exist() -> None:
    assert (AUDIT_PROTOCOLS / "dux6-residual-readability.md").is_file()
    assert "dux6-residual-readability.md" in (
        AUDIT_PROTOCOLS / "dux5-copy-dictionary.md"
    ).read_text(encoding="utf-8")


def test_no_developer_tokens_or_endpoints_in_text_bodies() -> None:
    endpoint_re = re.compile(r"GET\s+/ops/", re.I)
    for path in sorted(DASH.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in _walk(data.get("panels")):
            if panel.get("type") != "text" or panel.get("id") == 1000:
                continue
            content = (panel.get("options") or {}).get("content") or ""
            if not isinstance(content, str):
                continue
            assert "VALID_EMPTY" not in content, path.name
            assert not endpoint_re.search(content), path.name
            assert "### " not in content and not content.lstrip().startswith("###")


def test_run_explorer_orientation_is_compact_html() -> None:
    data = json.loads(
        (DASH / "bioetl-run-explorer-v1.json").read_text(encoding="utf-8")
    )
    for panel in _walk(data.get("panels")):
        title = panel.get("title") or ""
        if title == "Provenance · Run Scope" or title.startswith("Next actions"):
            opts = panel.get("options") or {}
            content = opts.get("content") or ""
            assert opts.get("mode") == "html"
            assert len(content) < 700
            if title == "Provenance · Run Scope":
                assert "font-size:16px" in content
                assert "font-size:18px" in content
                assert "overflow-wrap:anywhere" in content
            else:
                assert "overflow:hidden" in content or "font-size:12px" in content


def test_provenance_panels_share_readability_contract() -> None:
    specs = {
        "bioetl-control-plane-v1.json": 9400,
        "bioetl-overview-v2.json": 99,
        "bioetl-runtime.json": 9400,
        "bioetl-provider-health-v2.json": 9400,
        "bioetl-dq-v2.json": 9400,
        "bioetl-incident-v1.json": 9400,
        "bioetl-run-explorer-v1.json": 1,
    }
    required_css = (
        "padding:6px 10px",
        "border-left:4px solid #ff9830",
        "background:rgba(255,152,48,0.08)",
        "font-size:16px",
        "font-size:18px",
        "line-height:1.35",
        "white-space:normal",
        "overflow-wrap:anywhere",
        "max-width:96ch",
    )

    for filename, panel_id in specs.items():
        data = json.loads((DASH / filename).read_text(encoding="utf-8"))
        panels = {panel.get("id"): panel for panel in _walk(data.get("panels"))}
        provenance = panels[panel_id]
        content = str((provenance.get("options") or {}).get("content") or "")

        min_h = (
            3
            if filename
            in {"bioetl-overview-v2.json", "bioetl-run-explorer-v1.json"}
            else 4
        )
        assert provenance.get("gridPos", {}).get("h", 0) >= min_h, filename
        assert provenance.get("options", {}).get("mode") == "html", filename
        assert '<div style="font-size:18px;font-weight:700">' in content, filename
        assert all(token in content for token in required_css), filename
        assert "white-space:nowrap" not in content, filename
        assert "font-size:12px" not in content, filename

        status = next(
            (
                panel
                for panel in data.get("panels", [])
                if panel.get("title") == "Status"
            ),
            None,
        )
        if status is not None:
            assert status.get("gridPos", {}).get("h") == 4, filename
            assert status.get("gridPos", {}).get("y") == provenance.get(
                "gridPos", {}
            ).get("y"), filename


def test_browse_hides_raw_path_columns() -> None:
    data = json.loads(
        (DASH / "bioetl-run-explorer-v1.json").read_text(encoding="utf-8")
    )
    browse = next(p for p in _walk(data.get("panels")) if p.get("id") == 3010)
    transforms = browse.get("transformations") or []
    organize = next(t for t in transforms if t.get("id") == "organize")
    exclude = (organize.get("options") or {}).get("excludeByName") or {}
    assert exclude.get("json_path") is True
    assert exclude.get("markdown_path") is True
    assert exclude.get("row_kind") is True


def test_pfill_12_browse_explains_artifact_backing_and_backend_failure() -> None:
    data = json.loads(
        (DASH / "bioetl-run-explorer-v1.json").read_text(encoding="utf-8")
    )
    browse = next(
        panel for panel in _walk(data.get("panels")) if panel.get("id") == 3010
    )
    defaults = (browse.get("fieldConfig") or {}).get("defaults") or {}
    no_value = str(defaults.get("noValue") or "")
    description = str(browse.get("description") or "")
    target = (browse.get("targets") or [])[0]

    assert no_value.startswith("VALID EMPTY — no pipeline-run-report artifacts")
    assert "selected pipeline" in no_value
    assert "$pipeline" not in no_value
    assert "reports/run-reports/pipeline/<name>/" in no_value
    # Operator help distinguishes valid empty vs backend unavailable (#7248)
    # and bind/origin TREE_MISSING from a selector miss.
    assert "empty table is valid" in description.lower()
    assert "tree_missing" in description.lower()
    assert "verify_report_bind.py" in description
    assert "/health/live" in description
    assert "not a workflow" in description.lower()
    assert "chembl_baseline" in description
    assert "workflow-run-reports" in description
    assert target.get("root_selector") == "items"
    assert target.get("url") == (
        "/ops/observability/pipeline-run-reports?pipeline=${pipeline}&limit=10"
    )
    status_override = next(
        item
        for item in (browse.get("fieldConfig") or {}).get("overrides") or []
        if (item.get("matcher") or {}).get("options") == "status"
    )
    mapped = {
        key
        for prop in status_override.get("properties") or []
        if prop.get("id") == "mappings"
        for entry in prop.get("value") or []
        for key in (entry.get("options") or {})
    }
    assert {"TREE_MISSING", "LAYOUT_UNHEALTHY", "IDENTITY_UNHEALTHY"} <= mapped


def test_pfill_12_workflow_browser_is_not_panel_3010() -> None:
    data = json.loads(
        (DASH / "bioetl-run-explorer-v1.json").read_text(encoding="utf-8")
    )
    workflow = next(
        panel for panel in _walk(data.get("panels")) if panel.get("id") == 3020
    )
    defaults = (workflow.get("fieldConfig") or {}).get("defaults") or {}
    no_value = str(defaults.get("noValue") or "")
    target = (workflow.get("targets") or [])[0]
    assert workflow.get("title") == "Inspect Recent Workflow Runs (last 20)"
    assert no_value.startswith("VALID EMPTY — no workflow-run-report artifacts")
    assert "selected workflow" in no_value
    assert "$workflow" not in no_value
    assert target.get("url") == (
        "/ops/observability/workflow-run-reports?workflow=${workflow}&limit=20"
    )
    assert "tree_missing" in str(workflow.get("description") or "").lower()
    # 3010 must stay pipeline-only.
    browse = next(
        panel for panel in _walk(data.get("panels")) if panel.get("id") == 3010
    )
    browse_url = ((browse.get("targets") or [])[0]).get("url")
    assert "pipeline-run-reports" in str(browse_url)
    assert "workflow-run-reports" not in str(browse_url)


def test_pfill_11_dq_freshness_missing_series_is_explicit() -> None:
    data = json.loads((DASH / "bioetl-dq-v2.json").read_text(encoding="utf-8"))
    freshness = next(
        panel for panel in _walk(data.get("panels")) if panel.get("id") == 8
    )
    defaults = (freshness.get("fieldConfig") or {}).get("defaults") or {}
    expressions = [
        str(target.get("expr") or "") for target in freshness.get("targets") or []
    ]

    assert defaults.get("noValue") == (
        "TELEMETRY MISSING — no bioetl_data_freshness_seconds for scope"
    )
    assert any("bioetl_data_freshness_seconds" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions)
    assert "telemetry missing" in str(freshness.get("description") or "").lower()


def test_pfill_10_provider_missing_series_has_reason_and_action() -> None:
    data = json.loads(
        (DASH / "bioetl-provider-health-v2.json").read_text(encoding="utf-8")
    )
    panels = {panel.get("id"): panel for panel in _walk(data.get("panels"))}
    status = panels[9401]
    matrix = panels[9101]
    freshness = panels[9104]

    for panel in (status, matrix):
        description = str(panel.get("description") or "").lower()
        assert "telemetry missing" in description
        assert "healthy fleet" in description
    freshness_expr = str((freshness.get("targets") or [])[0].get("expr") or "")
    assert "bioetl_provider_current_status" in freshness_expr
    assert "or vector(0)" not in freshness_expr
    assert "fail-closed unknown" in str(freshness.get("description") or "").lower()


def test_percent_scores_integer_precision() -> None:
    for path in sorted(DASH.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in _walk(data.get("panels")):
            defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
            if defaults.get("unit") in {"percent", "percentunit"}:
                dec = defaults.get("decimals")
                if dec is not None:
                    assert int(dec) == 0, f"{path.name}:{panel.get('title')}"


def test_primary_status_documents_unknown_class() -> None:
    for path, status_id in (
        (DASH / "bioetl-control-plane-v1.json", 9401),
        (DASH / "bioetl-dq-v2.json", 9401),
        (DASH / "bioetl-overview-v2.json", 214),
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        status = next(p for p in _walk(data.get("panels")) if p.get("id") == status_id)
        desc = (status.get("description") or "").lower()
        assert "unknown" in desc
        assert "evidence incomplete" in desc or "missing" in desc


def test_dux6_run_context_collapsed_outside_explorer() -> None:
    expected_by_uid = {
        "bioetl-runtime": True,
        "bioetl-overview-v2": True,
    }
    for path in sorted(DASH.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = expected_by_uid.get(data.get("uid"))
        if expected is None:
            continue
        for panel in _walk(data.get("panels")):
            if (
                panel.get("type") == "row"
                and "run context" in (panel.get("title") or "").lower()
            ):
                assert panel.get("collapsed") is expected
