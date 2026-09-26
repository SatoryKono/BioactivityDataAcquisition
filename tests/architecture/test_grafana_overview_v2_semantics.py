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
    d = json.loads(
        Path("grafana/dashboards/bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    panels = _panels(d)
    titles = [p.get("title") for p in panels]
    assert titles.count("Monitor Scope Health") == 0
    assert titles.count("Review First Action") == 0
    assert titles.count("Review Run Domains") == 1
    row_labels = " ".join(
        p.get("title", "") for p in d.get("panels", []) if p.get("type") == "row"
    )
    assert "Range Evidence" not in row_labels
    assert "Inspect Run Context" in row_labels
    assert "Inspect Saved Run Evidence" in row_labels

    nav_links = list(d.get("links", []))
    links_blob = ""
    for panel in panels:
        if panel.get("id") == 1000:
            nav_links.extend(panel.get("links", []))
            links_blob = str(panel.get("options", {}).get("content", ""))
    links = " ".join(link.get("title", "") for link in nav_links) + links_blob
    # Full portfolio bus 0–6, with Run Explorer first.
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
        "Monitor Scope Health",
        "Review First Action",
        "Review Control Plane Status",
        "Review Runtime Status",
        "Review Data Quality Status",
        "Review Data Validation Status",
        "Review Workflow Status",
    ]:
        assert current_title not in titles
        continue
        p = next(x for x in panels if x.get("title") == current_title)
        expr = "\n".join(t.get("expr", "") for t in p.get("targets", []))
        assert "$__range" not in expr
