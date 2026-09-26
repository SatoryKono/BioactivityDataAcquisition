"""Operator-approved recent-run column order and exact identity handoffs."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_ten_columns_keep_full_identity_for_handoffs():
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 3010)
    organize = next(
        t["options"] for t in panel["transformations"] if t["id"] == "organize"
    )
    assert list(organize["renameByName"].values()) == [
        "Workflow",
        "Pipeline",
        "Provider",
        "Run ID",
        "Started",
        "Duration",
        "Overview",
        "Saved Evidence",
        "Data Quality",
        "Replay Readiness",
    ]
    overrides = {
        o["matcher"]["options"]: {p["id"]: p["value"] for p in o["properties"]}
        for o in panel["fieldConfig"]["overrides"]
    }
    for column in (
        "Overview",
        "Saved Evidence",
        "Data Quality",
        "Replay Readiness",
        "Provider",
    ):
        url = overrides[column]["links"][0]["url"]
        assert "${__data.fields.run_id:percentencode}" in url
        assert "${__data.fields.Pipeline:percentencode}" in url
        assert "${__data.fields.workflow_scope:percentencode}" in url
    assert "report_url:raw" in overrides["Run ID"]["links"][0]["url"]
    assert overrides["Started"]["unit"] == "time:YY-MM-DD:HH:mm"
    assert panel["options"]["sortBy"] == [{"displayName": "Started", "desc": True}]
    assert overrides["run_id"]["custom.hidden"] is True


@pytest.mark.parametrize(
    "uid,title",
    [
        ("bioetl-control-plane-v1", "Replay Readiness"),
        ("bioetl-overview-v2", "Run Overview"),
        ("bioetl-dq-v2", "Data Quality"),
    ],
)
def test_dashboard_names_preserve_uids(uid, title):
    dashboard = json.loads(
        Path(f"grafana/dashboards/{uid}.json").read_text(encoding="utf-8")
    )
    assert dashboard["title"] == title
    assert dashboard["uid"] == uid
