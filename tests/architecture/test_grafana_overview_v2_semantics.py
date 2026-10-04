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
    for title in (
        "Review Run Identity",
        "Review Provider Evidence",
        "Review Provider Check",
        "Inspect Selected Run Stages",
    ):
        assert titles.count(title) == 1

    nav_links = list(d.get("links", []))
    links_blob = ""
    for panel in panels:
        if panel.get("id") == 1000:
            nav_links.extend(panel.get("links", []))
            links_blob = str(panel.get("options", {}).get("content", ""))
    links = " ".join(link.get("title", "") for link in nav_links) + links_blob
    # Approved five-dashboard portfolio: DQ is a contextual Run Domains action.
    for token in [
        "Replay Readiness",
        "Run Overview",
        "Incident Workspace",
        "Run Explorer",
    ]:
        assert token in links
    assert 'aria-current="page"' in links_blob
    assert "bioetl-provider-health-v2" not in links
    assert "/d/bioetl-runtime" not in links
    domains = next(panel for panel in panels if panel.get("id") == 9002)
    domain_links = json.dumps(domains)
    for target in ("bioetl-control-plane-v1", "bioetl-dq-v2"):
        assert f"/d/{target}/" in domain_links
    assert "${run_id:queryparam}" in domain_links
    assert "${__url_time_range}" in domain_links

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
