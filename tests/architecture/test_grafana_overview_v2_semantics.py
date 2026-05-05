import json
from pathlib import Path


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
    assert titles.count("System Status") == 1
    system = next(p for p in panels if p.get("title") == "System Status")
    expr = "\n".join(t.get("expr", "") for t in system.get("targets", []))
    assert "bioetl_l0_status" in expr
    assert "$__range" not in expr
    mapping = json.dumps(
        system.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    )
    for token in ["NO DATA / UNKNOWN", "OK", "DEGRADED", "FAILING / BROKEN"]:
        assert token in mapping

    assert titles.count("Next Action") == 1
    row_labels = " ".join(
        p.get("title", "") for p in d.get("panels", []) if p.get("type") == "row"
    )
    assert "Range Evidence" in row_labels
    assert "Diagnostics" in row_labels

    links = " ".join(l.get("title", "") for l in d.get("links", []))
    for token in ["Runtime", "Data Quality", "Provider", "Control Plane", "Workflow"]:
        assert token in links

    for current_title in [
        "System Status",
        "Next Action",
        "L0 Inputs",
        "Runtime Blockers Current",
        "DQ Status Current",
        "Gold Lifecycle Current",
        "Control Plane Current",
    ]:
        p = next(x for x in panels if x.get("title") == current_title)
        expr = "\n".join(t.get("expr", "") for t in p.get("targets", []))
        assert "$__range" not in expr
