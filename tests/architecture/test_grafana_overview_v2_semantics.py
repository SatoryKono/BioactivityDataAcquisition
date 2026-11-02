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
    by_id = {p["id"]: p for p in panels}
    assert by_id[9300]["title"] == "Review Run Identity"
    assert by_id[9460]["title"] == "Inspect Selected Run Stages"
    assert by_id[9480]["title"] == "Review Provider Evidence"
    for panel_id in (9002, 9300, 9480, 9460):
        urls = [target.get("url", "") for target in by_id[panel_id].get("targets", [])]
        assert urls and all("run_id=${run_id" in url for url in urls)
        assert all("/ops/observability/" in url for url in urls)

    nav_links = list(d.get("links", []))
    links_blob = ""
    for panel in panels:
        if panel.get("id") == 1000:
            nav_links.extend(panel.get("links", []))
            links_blob = str(panel.get("options", {}).get("content", ""))
    links = " ".join(link.get("title", "") for link in nav_links) + links_blob
    # ADR-053: the five-dashboard portfolio preserves selected-run handoffs.
    for token in [
        "Replay Readiness",
        "Run Overview",
        "Incident Workspace",
        "Run Explorer",
    ]:
        assert token in links

    # Data Quality is a contextual detail route rather than a global nav item.
    dq_links = [
        link
        for link in by_id[9002].get("links", [])
        if link.get("url", "").startswith("/d/bioetl-dq-v2/")
    ]
    assert len(dq_links) == 1
    assert "${run_id:queryparam}" in dq_links[0]["url"]
    assert "${pipeline:queryparam}" in dq_links[0]["url"]
    assert "${__url_time_range}" in dq_links[0]["url"]

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
