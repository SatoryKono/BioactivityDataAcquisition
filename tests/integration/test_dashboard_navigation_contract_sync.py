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
"""Consistency checks for dashboard navigation contract surfaces."""

from __future__ import annotations

from pathlib import Path
import json

import pytest
import yaml

pytestmark = pytest.mark.integration

_CONTRACT_PATH = Path("docs/03-guides/dashboards/contracts/navigation-links.yaml")
_NAV_DOC_PATH = Path("docs/03-guides/dashboards/navigation-contract.md")
_USAGE_DOC_PATH = Path("docs/03-guides/dashboards/dashboard-v2-usage.md")
_DASHBOARDS_DIR = Path("grafana/dashboards")


def _load_contract() -> dict[str, object]:
    return yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8"))


def test_navigation_contract_docs_reference_machine_readable_artifact() -> None:
    for path in (_NAV_DOC_PATH, _USAGE_DOC_PATH):
        text = path.read_text(encoding="utf-8")
        assert "contracts/navigation-links.yaml" in text


def test_navigation_contract_uids_match_shipped_dashboards() -> None:
    contract = _load_contract()
    required_links = contract["required_top_level_links_by_uid"]
    assert isinstance(required_links, dict)

    contract_uids = set(required_links.keys())
    shipped_uids: set[str] = set()

    for dashboard_path in _DASHBOARDS_DIR.glob("*.json"):
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must define string uid"
        shipped_uids.add(uid)

    assert contract_uids == shipped_uids


def test_required_inbound_paths_match_overview_first_action_mirror() -> None:
    contract = _load_contract()
    target_uids = (
        "bioetl-runtime",
        "bioetl-control-plane-v1",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
    )
    route = {
        "source_uid": "bioetl-overview-v2",
        "source_panel_id": 215,
        "source_panel_title": "Review First Action",
        "source_status_row_panel_title_matcher": "^Inspect Scope & Evidence$",
    }
    assert contract["required_discoverable_inbound_paths"] == {
        "L1": {target_uid: [route] for target_uid in target_uids}
    }

    narrative = _NAV_DOC_PATH.read_text(encoding="utf-8")
    for target_uid in target_uids:
        expected_row = (
            f"| `{target_uid}` | `bioetl-overview-v2` | `215` | "
            "`Review First Action` | `^Inspect Scope & Evidence$` |"
        )
        assert expected_row in narrative

    overview = json.loads(
        (_DASHBOARDS_DIR / "bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    first_action = next(panel for panel in overview["panels"] if panel.get("id") == 215)
    urls = {
        str(link.get("url", ""))
        for link in first_action.get("options", {}).get("dataLinks", [])
    }
    for target_uid in target_uids:
        assert any(url.startswith(f"/d/{target_uid}/") for url in urls)
