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
    assert titles.count("Monitor Fleet Health") == 1
    system = next(p for p in panels if p.get("title") == "Monitor Fleet Health")
    expr = "\n".join(t.get("expr", "") for t in system.get("targets", []))
    assert "bioetl_l0_status" in expr
    assert "$__range" not in expr
    mapping = json.dumps(
        system.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    )
    for token in ["UNKNOWN", "OK", "WARN", "CRIT"]:
        assert token in mapping

    assert titles.count("Review First Action") == 1
    row_labels = " ".join(
        p.get("title", "") for p in d.get("panels", []) if p.get("type") == "row"
    )
    assert "Range Evidence" in row_labels
    assert any(
        label in row_labels for label in ("Diagnostics & Docs", "Domain status matrix")
    )

    nav_links = list(d.get("links", []))
    for panel in panels:
        if panel.get("id") == 1000:
            nav_links.extend(panel.get("links", []))
    links = " ".join(link.get("title", "") for link in nav_links)
    # Full portfolio bus 0–6 (Provider on-bus; Incident + Run Explorer adjuncts).
    for token in [
        "Trust",
        "Pipeline Diagnostics",
        "Provider Health",
        "Data Quality",
        "Incident Workspace",
        "Run Explorer",
    ]:
        assert token in links

    for current_title in [
        "Monitor Fleet Health",
        "Review First Action",
        "Inputs",
        "Runtime",
        "Data Quality",
        "Data Validation",
        "Control Plane",
    ]:
        p = next(x for x in panels if x.get("title") == current_title)
        expr = "\n".join(t.get("expr", "") for t in p.get("targets", []))
        assert "$__range" not in expr
