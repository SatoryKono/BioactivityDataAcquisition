"""Regression contracts for selector serialization and actionable row fields."""

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana.dashboard_context_links import build_handoff_url

pytestmark = pytest.mark.integration


def panels(payload):
    for panel in payload.get("panels", []):
        yield panel
        yield from panels(panel)


@pytest.mark.parametrize("path", sorted(Path("grafana/dashboards").glob("*.json")))
def test_navigation_preserves_selector_url_values(path: Path) -> None:
    if path.name == "bioetl-run-explorer-v1.json":
        return
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    nav = next(p for p in panels(dashboard) if p["id"] == 1000)
    for link in nav["links"]:
        assert "${run_type:queryparam}" in link["url"]
        assert "${workflow:queryparam}" in link["url"]
        assert "${__url_time_range}" in link["url"]


@pytest.mark.parametrize("path", sorted(Path("grafana/dashboards").glob("*.json")))
def test_range_action_keeps_its_frame_fields(path: Path) -> None:
    for panel in panels(json.loads(path.read_text(encoding="utf-8"))):
        if not any(
            t.get("root_selector") == "summary" for t in panel.get("targets", [])
        ):
            continue
        # Retention 9416 also reads a JSON `summary` object for OK/UNKNOWN
        # counts; that is not the selected-run range action.
        blob = json.dumps(panel)
        if "from_ms" not in blob:
            continue
        for name in ("from_ms", "to_ms"):
            assert all(
                not t.get("options", {}).get("excludeByName", {}).get(name)
                for t in panel.get("transformations", [])
            )
            override = next(
                o
                for o in panel["fieldConfig"]["overrides"]
                if o["matcher"]["options"] == name
            )
            assert {"id": "custom.hidden", "value": True} in override["properties"]


def test_recent_report_column_uses_the_row_http_link() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next(p for p in panels(dashboard) if p["id"] == 3010)
    override = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Report"
    )
    links = next(p["value"] for p in override["properties"] if p["id"] == "links")
    assert len(links) == 1
    assert links[0]["url"] == "${__data.fields.report_url:raw}"
    assert links[0]["targetBlank"] is True


def test_concrete_context_values_are_not_grafana_globs() -> None:
    url = build_handoff_url("bioetl-runtime")
    assert "${run_type:queryparam}" in url
    assert "var-run_type=$run_type" not in url


def test_ranked_action_overrides_inspect_value_with_domain_link() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text(encoding="utf-8")
    )
    panel = next(p for p in panels(dashboard) if p["id"] == 2010)
    override = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Action"
    )
    links = next(p["value"] for p in override["properties"] if p["id"] == "links")
    assert len(links) == 1
    assert "${__data.fields.route_pipeline:percentencode}" in links[0]["url"]
    assert "var-run_id=-" in links[0]["url"]
    assert "${__data.fields.action_scope}" in links[0]["url"]
    assert {"id": "custom.inspect", "value": False} in override["properties"]
    details = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Details"
    )
    assert {"id": "custom.inspect", "value": True} in details["properties"]
    assert {"id": "custom.hidden", "value": True} in details["properties"]
    evidence = next(p for p in panels(dashboard) if p["id"] == 22010)
    signal = next(
        o
        for o in evidence["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Signal"
    )
    assert {"id": "custom.wrapText", "value": True} in signal["properties"]
    assert {"id": "links", "value": []} in signal["properties"]
    assert {"id": "links", "value": []} in details["properties"]
    extractor = next(t for t in panel["transformations"] if t["id"] == "extractFields")
    assert extractor["options"]["source"] == "signal"
    assert extractor["options"]["regExp"] == "/(?<action_detail>.*)/"
    assert extractor["options"]["replace"] is False


def test_run_explorer_styles_processing_without_obsolete_columns() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next(p for p in panels(dashboard) if p["id"] == 3010)
    props = {
        o["matcher"]["options"]: {p["id"]: p["value"] for p in o["properties"]}
        for o in panel["fieldConfig"]["overrides"]
    }
    assert "Status" not in props and "Severity" not in props
    assert props["Processing"]["custom.cellOptions"]["type"] == "color-background"
    mappings = props["Processing"]["mappings"][0]["options"]
    assert mappings["failed"]["color"] == "red"
    assert mappings["unfinished"]["text"] == "unfinished"
    assert props["Replay readiness"]["noValue"] != "OK"

    assert props["Pipeline"]["custom.cellOptions"]["wrapText"] is False
    assert props["Pipeline"]["custom.inspect"] is True
    assert panel["options"]["footer"]["enablePagination"] is False


def test_run_explorer_hidden_fields_cannot_enable_table_wide_wrapping() -> None:
    """Grafana 12 TableRT applies one field's wrap option to every row cell."""
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next(p for p in panels(dashboard) if p["id"] == 3010)
    assert not panel["fieldConfig"]["defaults"]["custom"]["cellOptions"].get("wrapText")
    for override in panel["fieldConfig"]["overrides"]:
        for prop in override["properties"]:
            if prop["id"] == "custom.cellOptions":
                assert not prop["value"].get("wrapText"), override["matcher"]
