"""Replay simplification must retain diagnostics and exact-run evidence scope."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration



def test_replay_layout_preserves_checks_and_identity_scope():
    root = Path(__file__).resolve().parents[2]
    dashboard = json.loads(
        (root / "grafana/dashboards/bioetl-control-plane-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panels = dashboard["panels"]
    pending = list(panels)
    by_id = {}
    while pending:
        panel = pending.pop()
        assert panel["id"] not in by_id
        by_id[panel["id"]] = panel
        pending.extend(panel.get("panels", []))
    assert {9413, 9414, 9415, 9416, 9406, 9422, 9423, 9408} <= by_id.keys()
    assert not (
        {9402, 9403, 9405, 9407, 9409, 9410, 9411, 9417, 9421, 139} & by_id.keys()
    )
    assert by_id[9423] in panels
    assert by_id[9423]["gridPos"]["y"] < by_id[9408]["gridPos"]["y"]
    assert "priority=" not in by_id[9408]["targets"][0]["url"]
    assert "present ? 1 : 0" in by_id[9408]["targets"][0]["uql"]
    for panel in by_id.values():
        for target in panel.get("targets", []):
            assert "run_id=${run_id}" in target["url"]
    assert {p["id"] for p in by_id[9430]["panels"]} == {9414, 9415, 9416}
    assert {p["id"] for p in by_id[9431]["panels"]} == {9413, 9406}
