"""Preserve coverage semantics while allocating enough rows for their labels."""

from copy import deepcopy

from scripts.ops.observability.grafana._audit_presentation import (
    stamp_audit_presentation,
)


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
