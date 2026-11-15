"""Preserve coverage semantics while allocating enough rows for their labels."""

from copy import deepcopy

from scripts.ops.observability.grafana._audit_presentation import (
    stamp_audit_presentation,
)
from scripts.ops.observability.grafana._v2_model_parity import _layout


def test_coverage_expansion_moves_following_sections_once_without_changing_queries():
    def panel(pid, x):
        return {
            "id": pid,
            "type": "stat",
            "gridPos": {"x": x, "y": 5, "w": 8, "h": 3},
            "options": {"orientation": "horizontal", "textMode": "value_and_name"},
            "targets": [{"expr": "observed_coverage", "refId": "A"}],
            "fieldConfig": {"defaults": {"noValue": "UNKNOWN", "mappings": []}},
        }

    dashboard = {
        "uid": "bioetl-incident-v1",
        "panels": [
            {
                "id": 8809,
                "type": "row",
                "gridPos": {"x": 0, "y": 4, "w": 24, "h": 1},
                "panels": [panel(9102, 0), panel(9491, 16)],
            },
            {
                "id": 9990,
                "type": "row",
                "gridPos": {"x": 0, "y": 8, "w": 24, "h": 1},
                "panels": [
                    {
                        "id": 9991,
                        "type": "text",
                        "gridPos": {"x": 0, "y": 9, "w": 24, "h": 2},
                    }
                ],
            },
        ],
    }
    original = deepcopy(dashboard)
    stamp_audit_presentation(dashboard)
    children = dashboard["panels"][0]["panels"]
    bottom = max(p["gridPos"]["y"] + p["gridPos"]["h"] for p in children)
    assert bottom <= dashboard["panels"][1]["gridPos"]["y"]
    assert dashboard["panels"][1]["panels"][0]["gridPos"]["y"] == bottom + 1
    for previous, current in zip(
        original["panels"][0]["panels"], children, strict=True
    ):
        assert current["targets"] == previous["targets"]
        assert current["fieldConfig"] == previous["fieldConfig"]
    first = deepcopy(dashboard)
    stamp_audit_presentation(dashboard)
    assert dashboard == first


def test_expanded_coverage_row_matches_grafana_v2_wire_order():
    def card(pid, x, y, height):
        return {
            "id": pid,
            "type": "stat",
            "gridPos": {"x": x, "y": y, "w": 8, "h": height},
            "options": {},
            "targets": [{"expr": f"evidence_{pid}", "refId": "A"}],
        }

    row = {
        "id": 8809,
        "type": "row",
        "gridPos": {"x": 0, "y": 4, "w": 24, "h": 1},
        "panels": [card(9102, 0, 7, 3), card(9491, 16, 7, 3), card(894, 12, 5, 2)],
    }
    dashboard = {"uid": "bioetl-incident-v1", "panels": [row]}
    queries = {p["id"]: deepcopy(p["targets"]) for p in row["panels"]}
    stamp_audit_presentation(dashboard)
    # Actual Grafana v2 keeps source array order; the independent parity
    # contract requires the logical grid order. Both must describe one layout.
    wire_order = [f"panel-{p['id']}" for p in row["panels"]]
    layout = _layout(dashboard["panels"])
    expected = layout["spec"]["rows"][0]["spec"]["layout"]["spec"]["items"]
    assert wire_order == [item["spec"]["element"]["name"] for item in expected]
    assert {p["id"]: p["targets"] for p in row["panels"]} == queries
