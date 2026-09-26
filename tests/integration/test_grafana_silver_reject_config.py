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
"""Silver-reject surface contracts after Explorer retirement (2026-07-23).

Previously this module used a module-level pytest.skip that greenwashed both
retired Explorer cases and live DQ reject panel contracts after the DQ v2
retitle. Keep absence + current-title contracts only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = [pytest.mark.integration]

_DASHBOARD_DIR = Path("grafana/dashboards")
_RETIRED_EXPLORER = "bioetl-silver-reject-explorer.json"
_DQ = _DASHBOARD_DIR / "bioetl-dq-v2.json"


def test_silver_reject_explorer_dashboard_is_not_shipped() -> None:
    """Explorer JSON must stay off the shipping dashboard set."""
    assert not (_DASHBOARD_DIR / _RETIRED_EXPLORER).exists()


def test_shipped_dashboards_do_not_handoff_to_silver_reject_explorer() -> None:
    """No remaining deep-links/uids to the retired Explorer surface."""
    offenders: list[str] = []
    for path in sorted(_DASHBOARD_DIR.glob("*.json")):
        blob = path.read_text(encoding="utf-8")
        if "bioetl-silver-reject-explorer" in blob:
            offenders.append(path.as_posix())
    assert offenders == []


def test_dq_v2_exposes_current_silver_reject_evidence_panels() -> None:
    """Live DQ reject evidence uses the post-retitle panel names."""
    dashboard = load_dashboard(_DQ)
    titles = {panel.get("title") for panel in get_dashboard_panels(dashboard)}
    required = {
        "Monitor Silver Filter Rejects",
        "Monitor Silver Reject Mismatch",
        "Inspect Top Silver Reject Reasons",
        "Inspect Top Silver Reject Fields",
        "Inspect Silver Rejects by Pipeline",
    }
    missing = sorted(required - titles)
    assert missing == [], f"DQ v2 missing silver-reject evidence panels: {missing}"


def test_dq_v2_silver_reject_mismatch_is_background_stat() -> None:
    """Accounting mismatch remains a high-visibility monitor."""
    dashboard = load_dashboard(_DQ)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Silver Reject Mismatch"
        ),
        None,
    )
    assert panel is not None
    assert panel.get("type") == "stat"
    assert panel.get("options", {}).get("colorMode") in {
        "background",
        "backgroundSolid",
        "value",
    }


def test_dq_v2_json_is_parseable_and_has_stable_uid() -> None:
    dashboard = json.loads(_DQ.read_text(encoding="utf-8"))
    assert dashboard.get("uid")
    assert isinstance(dashboard.get("panels"), list)
    assert dashboard["panels"]
