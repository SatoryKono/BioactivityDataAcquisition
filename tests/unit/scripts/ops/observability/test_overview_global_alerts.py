"""LA-06: a missing run selection must never hide the fleet alert donor."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from scripts.ops.observability.grafana import render_nav_bus as nav
from scripts.ops.observability.grafana._overview_global_alerts import (
    embed_global_alerts,
)

pytestmark = pytest.mark.unit


def _load(name: str) -> dict:
    return json.loads(
        (nav.DASH_DIR / f"bioetl-{name}.json").read_text(encoding="utf-8")
    )


def test_global_alerts_retain_donor_query_and_complete_list() -> None:
    overview = _load("overview-v2")
    incident = _load("incident-v1")
    panels = {p["id"]: p for p in overview["panels"]}
    donor = next(p for p in incident["panels"] if p["id"] == 2005)
    summary = panels[2005]
    assert summary["targets"] == donor["targets"]
    assert summary["transformations"] == donor["transformations"]
    assert summary["fieldConfig"] == donor["fieldConfig"]
    # $1 is a PromQL capture replacement, never a dashboard selection.
    assert not re.search(
        r"\$(?:\{)?(?:run_id|pipeline|provider|workflow|run_type)",
        str(summary["targets"]),
    )
    assert summary["gridPos"] == {"x": 0, "y": 19, "w": 24, "h": 4}
    assert "repeat" not in summary
    assert panels[32005]["collapsed"] is True
    full = panels[32005]["panels"][0]
    assert full["id"] == 22005
    assert full["targets"][0]["panelId"] == 2005
    assert full["targets"][0]["withTransforms"] is False
    assert all(t["id"] != "limit" for t in full["transformations"])
    for panel in (summary, full):
        link = panel["links"][0]
        assert "/d/bioetl-incident-v1/" in link["url"]
        assert "var-run_id=-" in link["url"]
        assert "var-pipeline=$__all" in link["url"]
        assert "${__url_time_range}" in link["url"]
        assert link["includeVars"] is False


def test_embedding_preserves_local_queries_and_relative_layout() -> None:
    overview = _load("overview-v2")
    before = deepcopy(overview)
    incident = _load("incident-v1")
    donor_before = deepcopy(incident)
    embed_global_alerts(overview, incident)
    assert incident == donor_before
    after = {p["id"]: p for p in overview["panels"]}
    for panel in before["panels"]:
        if panel["id"] in {99, 2005, 32005}:
            continue
        assert after[panel["id"]] == panel
    # No two root panels occupy the same grid cells (collapsed children excluded).
    roots = overview["panels"]
    for index, panel in enumerate(roots):
        a = panel["gridPos"]
        for other in roots[index + 1 :]:
            b = other["gridPos"]
            assert (
                a["x"] + a["w"] <= b["x"]
                or b["x"] + b["w"] <= a["x"]
                or a["y"] + a["h"] <= b["y"]
                or b["y"] + b["h"] <= a["y"]
            )


def test_generator_rebuilds_global_alerts_without_changing_saved_run_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = nav.DASH_DIR
    for name in ("bioetl-overview-v2.json", "bioetl-incident-v1.json"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    target = tmp_path / "bioetl-overview-v2.json"
    original = json.loads(target.read_text(encoding="utf-8"))
    drifted = deepcopy(original)
    drifted["panels"] = [p for p in drifted["panels"] if p["id"] not in {2005, 32005}]
    target.write_text(json.dumps(drifted), encoding="utf-8")
    monkeypatch.setattr(nav, "DASH_DIR", tmp_path)
    assert not nav.apply_to_dashboard(
        target, current_uid="bioetl-overview-v2", check=True
    )
    assert nav.apply_to_dashboard(target, current_uid="bioetl-overview-v2")
    rebuilt = json.loads(target.read_text(encoding="utf-8"))
    assert rebuilt == original
    assert nav.apply_to_dashboard(target, current_uid="bioetl-overview-v2", check=True)
