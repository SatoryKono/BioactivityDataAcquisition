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
    dashboard = load_dashboard(_DQ)
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9403)
    target = panel["targets"][0]
    assert "/ops/observability/processed-records?" in target["url"]
    assert "run_id=${run_id}" in target["url"]
    stage_input = next(t for t in panel["targets"] if t["refId"] == "StageInput")
    for outcome in (
        "silver_filtered_out_records",
        "silver_quarantined_records",
        "silver_deduplicated_records",
    ):
        assert outcome in stage_input["uql"]
    assert all("expr" not in t for t in panel["targets"])
    assert panel["gridPos"]["h"] == 14
    assert not any(t["id"] == "limit" for t in panel["transformations"])


def test_dq_v2_silver_reject_mismatch_is_background_stat() -> None:
    dashboard = load_dashboard(_DQ)
    assert not any(
        p["title"] == "Monitor Silver Reject Mismatch"
        for p in get_dashboard_panels(dashboard)
    )
    # Saved accounting never borrows a current fleet mismatch stat as this run's verdict.
    status = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9406)
    assert "run_id=${run_id}" in status["targets"][0]["url"]
    assert status["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"


def test_dq_v2_json_is_parseable_and_has_stable_uid() -> None:
    dashboard = json.loads(_DQ.read_text(encoding="utf-8"))
    assert dashboard.get("uid")
    assert isinstance(dashboard.get("panels"), list)
    assert dashboard["panels"]
