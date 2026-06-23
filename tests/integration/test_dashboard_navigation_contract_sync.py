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
