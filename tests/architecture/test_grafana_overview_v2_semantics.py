import pytest

import json
from pathlib import Path


pytestmark = pytest.mark.architecture


def _panels(d):
    out = []
    for p in d.get("panels", []):
        out.append(p)
        if p.get("type") == "row":
            out.extend(p.get("panels", []))
    return out


def test_overview_v2_semantics_contract():
    d = json.loads(Path("grafana/dashboards/bioetl-overview-v2.json").read_text())
    panels = _panels(d)
    titles = [p.get("title") for p in panels]
    assert titles.count("Status") == 1
    system = next(p for p in panels if p.get("title") == "Status")
    expr = "\n".join(t.get("expr", "") for t in system.get("targets", []))
    assert "bioetl_l0_status" in expr
    assert "$__range" not in expr
    mapping = json.dumps(
        system.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    )
    for token in ["UNKNOWN", "OK", "WARN", "CRIT"]:
        assert token in mapping

    assert titles.count("First Action") == 1
    row_labels = " ".join(
        p.get("title", "") for p in d.get("panels", []) if p.get("type") == "row"
    )
    assert "Range Evidence" in row_labels
    assert "Diagnostics" in row_labels

    nav_links = list(d.get("links", []))
    for panel in panels:
        if panel.get("id") == 1000:
            nav_links.extend(panel.get("links", []))
    links = " ".join(link.get("title", "") for link in nav_links)
    # Primary 5-dashboard diet bus (Trust / Overview / Pipeline Diagnostics / DQ).
    # Provider remains interim/off-bus; Runtime handoff is labeled Pipeline Diagnostics.
    for token in ["Trust", "Pipeline Diagnostics", "Data Quality"]:
        assert token in links

    for current_title in [
        "Status",
        "First Action",
        "Inputs",
        "Runtime",
        "Data Quality",
        "Data Validation",
        "Control Plane",
    ]:
        p = next(x for x in panels if x.get("title") == current_title)
        expr = "\n".join(t.get("expr", "") for t in p.get("targets", []))
        assert "$__range" not in expr
