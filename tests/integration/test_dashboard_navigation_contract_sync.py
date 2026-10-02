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
        "bioetl-control-plane-v1",
        "bioetl-dq-v2",
    )
    route = {
        "source_uid": "bioetl-overview-v2",
        "source_panel_id": 9002,
        "source_panel_title": "Run Domains",
        "source_status_row_panel_title_matcher": "^Inspect Scope & Evidence$",
    }
    assert contract["required_discoverable_inbound_paths"] == {
        "L1": {"bioetl-control-plane-v1": [route]},
        "L2": {"bioetl-dq-v2": [route]},
    }

    narrative = _NAV_DOC_PATH.read_text(encoding="utf-8")
    for target_uid in target_uids:
        expected_row = (
            f"| `{target_uid}` | `bioetl-overview-v2` | `9002` | "
            "`Run Domains` | `^Inspect Scope & Evidence$` |"
        )
        assert expected_row in narrative

    overview = json.loads(
        (_DASHBOARDS_DIR / "bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    first_action = next(
        panel for panel in overview["panels"] if panel.get("id") == 9002
    )
    urls = {str(link.get("url", "")) for link in (first_action.get("links") or [])}
    for target_uid in target_uids:
        assert any(url.startswith(f"/d/{target_uid}/") for url in urls)


@pytest.mark.parametrize("target_uid", ["bioetl-control-plane-v1", "bioetl-dq-v2"])
@pytest.mark.parametrize("damage", ["removed", "foreign_run", "implicit_vars"])
def test_selected_run_inbound_links_fail_closed(target_uid: str, damage: str) -> None:
    from tests.integration._grafana_dashboard_links_support import (
        _assert_inbound_route_policy,
    )

    dashboard = json.loads(
        (_DASHBOARDS_DIR / "bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 9002)
    link = next(link for link in panel["links"] if f"/d/{target_uid}/" in link["url"])
    if damage == "removed":
        panel["links"].remove(link)
        # The same route is also offered from table cells. Remove both copies
        # to model a genuinely missing inbound path, not only a hidden menu.
        panel["fieldConfig"]["defaults"]["links"] = [
            candidate
            for candidate in panel["fieldConfig"]["defaults"]["links"]
            if f"/d/{target_uid}/" not in candidate["url"]
        ]
    elif damage == "foreign_run":
        link["url"] = link["url"].replace(
            "${run_id:queryparam}", "var-run_id=foreign-run"
        )
    else:
        link["includeVars"] = True
    level = "L1" if target_uid == "bioetl-control-plane-v1" else "L2"
    route = _load_contract()["required_discoverable_inbound_paths"][level][target_uid][
        0
    ]
    with pytest.raises(AssertionError):
        _assert_inbound_route_policy(
            level_name=level,
            target_uid=target_uid,
            route=route,
            dashboards={"bioetl-overview-v2": dashboard},
        )


def test_replay_verdict_link_must_open_the_checks_panel() -> None:
    from tests.integration._grafana_dashboard_links_support import (
        _assert_critical_panel_entry,
    )

    path = _DASHBOARDS_DIR / "bioetl-control-plane-v1.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    panel = next(p for p in dashboard["panels"] if p["id"] == 9422)
    panel["links"][0]["url"] = panel["links"][0]["url"].replace(
        "viewPanel=9423", "viewPanel=9408"
    )
    entry = _load_contract()["required_panel_links_by_uid"]["bioetl-control-plane-v1"][
        0
    ]
    with pytest.raises(AssertionError, match="must open panel 9423"):
        _assert_critical_panel_entry(
            dashboard_path=path,
            uid=dashboard["uid"],
            panels_by_id={9422: panel},
            entry=entry,
        )
