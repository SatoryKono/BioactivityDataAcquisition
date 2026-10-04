"""Canonical schema migration preserves query/layout intent and explicit identity."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana.render_nav_bus import _migrate_grafana_schema42

pytestmark = pytest.mark.unit


def test_schema42_refs_preserve_queries_layout_and_static_panel_behavior():
    query = {"expr": "up{job='bioetl'}", "refId": "A"}
    payload = {
        "schemaVersion": 30,
        "timepicker": {"time_options": ["5m"]},
        "annotations": {"list": [{"datasource": "-- Grafana --"}]},
        "templating": {
            "list": [
                {
                    "name": "pipeline",
                    "datasource": "BioETL Ops HTTP",
                    "query": "/ops/catalog",
                }
            ]
        },
        "panels": [
            {
                "id": 1,
                "type": "text",
                "options": {"content": "static"},
                "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
            },
            {
                "id": 2,
                "type": "row",
                "panels": [
                    {
                        "id": 3,
                        "type": "timeseries",
                        "datasource": "Prometheus",
                        "targets": [query],
                        "gridPos": {"x": 0, "y": 3, "w": 12, "h": 8},
                    }
                ],
            },
        ],
    }
    before = copy.deepcopy(payload)
    _migrate_grafana_schema42(payload)
    assert payload["schemaVersion"] == 42
    assert payload["timepicker"] == {}
    assert payload["panels"][0] == before["panels"][0]
    panel = payload["panels"][1]["panels"][0]
    assert panel["gridPos"] == before["panels"][1]["panels"][0]["gridPos"]
    assert panel["targets"][0]["expr"] == query["expr"]
    assert panel["targets"][0]["refId"] == "A"
    assert (
        panel["datasource"]
        == panel["targets"][0]["datasource"]
        == {"type": "prometheus", "uid": "prometheus"}
    )
    assert payload["templating"]["list"][0]["query"] == "/ops/catalog"
    assert payload["templating"]["list"][0]["datasource"] == {
        "type": "yesoreyeram-infinity-datasource",
        "uid": "bioetl-ops-http",
    }
    assert payload["annotations"]["list"][0]["datasource"] == {"uid": "-- Grafana --"}
    migrated = copy.deepcopy(payload)
    _migrate_grafana_schema42(payload)
    assert payload == migrated


def test_explicit_target_reference_is_preserved_instead_of_inheriting_panel():
    explicit = {"type": "custom-plugin", "uid": "explicit-uid", "extra": "preserved"}
    payload = {
        "panels": [
            {"id": 1, "datasource": "Prometheus", "targets": [{"datasource": explicit}]}
        ]
    }
    _migrate_grafana_schema42(payload)
    assert payload["panels"][0]["targets"][0]["datasource"] is explicit
    assert explicit == {
        "type": "custom-plugin",
        "uid": "explicit-uid",
        "extra": "preserved",
    }


@pytest.mark.parametrize(
    "datasource", ["unprovisioned-name", {}, {"type": "prometheus"}, {"uid": ""}]
)
def test_unresolved_or_malformed_references_fail_closed(datasource):
    with pytest.raises(ValueError, match="datasource"):
        _migrate_grafana_schema42({"panels": [{"id": 1, "datasource": datasource}]})


def test_hidden_series_migration_matches_grafana42_tooltip_rule():
    hidden = {
        "id": "custom.hideFrom",
        "value": {"viz": True, "legend": True, "tooltip": False},
    }
    visible = {"id": "custom.hideFrom", "value": {"viz": False, "tooltip": False}}
    payload = {
        "panels": [
            {"id": 1, "fieldConfig": {"overrides": [{"properties": [hidden, visible]}]}}
        ]
    }
    _migrate_grafana_schema42(payload)
    assert hidden["value"]["tooltip"] is True
    assert visible["value"]["tooltip"] is False


def test_shipped_models_are_idempotent_and_do_not_add_static_queries():
    for path in Path("grafana/dashboards").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        before = copy.deepcopy(payload)
        _migrate_grafana_schema42(payload)
        assert payload == before, path
        assert payload["schemaVersion"] == 42
        pending = list(payload["panels"])
        while pending:
            panel = pending.pop()
            pending.extend(panel.get("panels", []))
            if panel.get("type") in {"text", "row"}:
                assert not panel.get("targets"), (path, panel["id"])
